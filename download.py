import requests
import os
import yaml

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
        
        return response.json()

class Course:

    def __init__(self, courseId, courseName):
        self.courseId = courseId
        self.courseName = courseName

    def download(self):
        print(f'  Getting available folders for {self.courseName}')
        self.folders = Download.getFolderInformation(self.courseId)
        for folder in self.folders:
            folder.download(self.courseName)


class Folder:
    
    def __init__(self, folderId, folderName, fullName):
        self.folderId = folderId
        self.folderName = folderName
        self.fullName = fullName

    def download(self, courseName):
        print(f'    Getting available files for {self.folderName}')
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
        if not LocalDirectory.canvasFileExists(self.savePath):
            # Download Files
            print('      New File detected - Downloading')
            response = requests.get(self.fileUrl)
            LocalDirectory.saveDownloadedFile(self.savePath, response.content)

class LocalDirectory:

    def canvasFileExists(savePath) -> bool:
        # Returns True if the Canva file already exists in the local directory
        path = Download.baseDirectory + '/' + savePath
        print('      ' + path)
        return os.path.isfile(path)

    def saveDownloadedFile(savePath, fileContent):
        path = Download.baseDirectory + '/' + savePath
        # Check if directory exists, create directory if not
        directory = os.path.dirname(path)
        if not os.path.isdir(directory):
            os.makedirs(directory)
        # Sanity check, we don't want to overwrite any existing files
        if os.path.exists(path):
            print("There's probably a bug somewhere")
            exit(1)
        with open(path, 'wb+') as f:
            f.write(fileContent)

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
                Download.baseDirectory = config['baseDirectory']
            except yaml.YAMLError as exc:
                print("Error loading config file")
                exit(1)

    def download(self):
        print("Getting available courses on Canvas")
        data = Download.apiConnection.sendGetRequest('api', 'v1', 'courses', enrollment_state = 'active')
        courses = [Course(courseId=course['id'], courseName=course['name']) for course in data if 'name' in course]
        for course in courses:
            course.download()

    '''
    Static Methods
    '''
            
    def getFolderInformation(courseId):
        # Get available folders
        # This returns a list of folders that includes sub folders as well
        data = Download.apiConnection.sendGetRequest('api', 'v1', 'courses', str(courseId), 'folders')
        folders = [Folder(folderId=folder['id'], folderName=folder['name'], fullName=folder['full_name']) 
            for folder in data if 'files_count' in folder and folder['files_count'] > 0]
        return folders

    def getFileInformation(folderId):
        data = Download.apiConnection.sendGetRequest('api', 'v1', 'folders', str(folderId), 'files')
        if 'status' in data:
            return []
        files = [File(fileId=file['id'], fileName=file['display_name'], fileUrl=file['url']) for file in data]
        return files


if __name__ == '__main__':
    download = Download()
    download.run()

