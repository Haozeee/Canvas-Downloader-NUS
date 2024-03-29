import requests
import os
import yaml
import zipfile
import time
import threading

class CanvasAPI:

    canvasURL = 'https://canvas.nus.edu.sg/'

    def setAuthenticationToken(self, token):
        self.requestHeader = {'Authorization' : 'Bearer ' + token}

    def sendGetRequest(self, *args, **kwags):
        if self.requestHeader is None:
            print('No authentication header')
            exit(1)
        
        requestURL = CanvasAPI.canvasURL + '/'.join(args)

        try:
            response = requests.get(requestURL, headers=self.requestHeader, params=kwags)
        except Exception as e:
            print('Error while making GET request')
            print(e)
            exit(1)

        return response.json() if response.status_code == 200 else []

class Course:

    def __init__(self, courseId, courseName):
        self.courseId = courseId
        self.courseName = courseName

    def download(self):
        print(f'Checking new files for {self.courseName}')
        self.folders = Download.getFolderInformation(self.courseId)
        for folder in self.folders:
            folder.download(self.courseName)


class Folder:
    
    def __init__(self, folderId, folderName, fullName):
        self.folderId = folderId
        self.folderName = folderName
        self.fullName = fullName

    def download(self, courseName):
        self.files = Download.getFileInformation(self.folderId)
        for file in self.files:
            file.download(courseName, self.fullName)

class File:
    
    def __init__(self, fileId, fileName, fileUrl):
        self.fileId = fileId
        self.fileName = fileName
        self.fileUrl = fileUrl

    def download(self, courseName, folderName):
        # Parse canvas naming converntion to what we want to store in local
        course = courseName.replace('/',' ').split(' ')[0]
        folder = '/'.join(folderName.split('/')[1:])
        self.savePath = course + '/' + (folder) + '/' + self.fileName
        # Handle the case when folder == ''
        self.savePath = self.savePath.replace('//', '/')

        # Check if file already exists
        if not LocalDirectory.canvasFileExists(self.savePath) and self.fileUrl != '':
            # Download Files
            print(f'New File detected - Downloading: {self.savePath}')
            response = requests.get(self.fileUrl)
            LocalDirectory.saveDownloadedFile(self.savePath, response.content)

class LocalDirectory:

    def canvasFileExists(savePath) -> bool:
        # Returns True if the Canva file already exists in the local directory
        path = Download.baseDirectory + '/' + savePath
        return os.path.isfile(path)

    def saveDownloadedFile(savePath, fileContent):
        saveLocation = Download.baseDirectory + '/' + savePath
        # Check if directory exists, create directory if not
        directory = os.path.dirname(saveLocation)
        if not os.path.isdir(directory):
            os.makedirs(directory)
        # Sanity check, we don't want to overwrite any existing files
        if os.path.exists(saveLocation):
            print("There's probably a bug somewhere")
            exit(1)
        with open(saveLocation, 'wb+') as f:
            f.write(fileContent)

        # Customise how different files are handled
        extension = os.path.splitext(saveLocation)[1]
        if extension == '.zip':
            LocalDirectory.handleZipFileDownload(saveLocation)
        elif extension == '.ppt' or extension == '.pptx':
            LocalDirectory.handlePowerpointDownloads(saveLocation)

    # Unzip file into a new directory
    def handleZipFileDownload(zipFileLocation):
        with zipfile.ZipFile(zipFileLocation, 'r') as zip:
            saveDirectory = os.path.splitext(zipFileLocation)[0]
            if not os.path.isdir(saveDirectory):
                os.makedirs(saveDirectory)
                zip.extractall(path=saveDirectory)

    # Create a copy of a powerpoint files as a pdf
    def handlePowerpointDownloads(pptFileLocation):
        pass

class Download:

    apiConnection = CanvasAPI()
    # Base directory where files should be stored
    baseDirectory = '~'

    def run(self):
        self.getConfigs()
        self.download()

    def getConfigs(self):
        with open('config.yml', 'r') as f:
            try:
                config = yaml.safe_load(f)
                Download.apiConnection.setAuthenticationToken(config['apiToken'])
                Download.baseDirectory = os.path.expanduser(config['baseDirectory'])
            except yaml.YAMLError as exc:
                print("Error loading config file")
                exit(1)

    def download(self):
        Download.filesDownloaded = 0
        print("Downloading new files from Canvas")
        data = Download.apiConnection.sendGetRequest('api', 'v1', 'courses', enrollment_state = 'active')
        courses = [course for course in data if 'name' in course]
        downloadThreads = []

        for course in courses:
            t = threading.Thread(target=Download.downloadCourse, args=(course['id'], course['name'],))
            t.start()
            downloadThreads.append(t)

        for t in downloadThreads:
            t.join()

    '''
    Static Methods
    '''

    def downloadCourse(courseId, courseName):
        course = Course(courseId, courseName)
        course.download()
            
    def getFolderInformation(courseId):
        # Get available folders
        # This returns a list of folders that includes sub folders as well
        data = Download.apiConnection.sendGetRequest('api', 'v1', 'courses', str(courseId), 'folders', per_page=100)
        folders = [Folder(folderId=folder['id'], folderName=folder['name'], fullName=folder['full_name']) 
            for folder in data if 'files_count' in folder and folder['files_count'] > 0]
        return folders

    def getFileInformation(folderId):
        data = Download.apiConnection.sendGetRequest('api', 'v1', 'folders', str(folderId), 'files', per_page=100)
        if 'status' in data:
            return []
        files = [File(fileId=file['id'], fileName=file['display_name'], fileUrl=file['url']) for file in data]
        return files

if __name__ == '__main__':
    start = time.time()
    download = Download()
    download.run()
    print(f'Time taken: {time.time() -  start:.2f} seconds')
