from __future__ import print_function
import pickle
import os.path
import os
import io
import sys

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from apiclient import errors

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive']
CAACFolder = '16leQlIP3Sfx4N5LJSAZtgFRYWx0xeg1O'


def auth(service):
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)
    return service


def listFiles(size, service):
    results = service.files().list(
        pageSize=size, fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])

    if not items:
        print('No files found.')
    else:
        print('Files:')
        for item in items:
            print(u'{0} ({1})'.format(item['name'], item['id']))


def fileUpload(service, filename, filepath, mimetype, folderID):
    file_metadata = {'name': filename,
                     'parents': [folderID]}
    media = MediaFileUpload(filepath,
                            mimetype=mimetype)
    file = service.files().create(body=file_metadata,
                                  media_body=media,
                                  fields='id').execute()
    return file


def fileRemove(service, fileID):
    service.files().delete(fileId=fileID).execute()


def fileDownload(service, fileID, filepath, mimetype=None, folderID=None):
    request = service.files().get_media(fileId=fileID)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print('Download {}%.'.format(int(status.progress() * 100)))
    with io.open(filepath, 'wb') as f:
        fh.seek(0)
        f.write(fh.read())


def searchFiles(size, service, filename, ids):
    results = service.files().list(pageSize=size, fields="nextPageToken, files(id, name)",
                                   q="name contains '{}' and trashed = false".format(filename)).execute()
    items = results.get('files', [])

    if not items:
        print('Não foram encontrados arquivos.')
    else:
        for item in items:
            ids.append(item['id'] + '\n')
        print('IDs dos arquivos gravados em foundIDs.txt')


def listFilesInFolder(service, folderID, ids):
    results = service.files().list(fields="nextPageToken, files(id, name)",
                                   q="'{}' in parents and trashed = false".format(folderID)).execute()
    items = results.get('files', [])

    if not items:
        print('Não foram encontrados arquivos.')
    else:
        for item in items:
            ids.append(item['id'] + '\n')


def searchFilesInFolder(service, folderID, filename, filenameOpt, ids, names):
    results = service.files().list(fields="nextPageToken, files(id, name)",
                                   q="'{}' in parents and (name contains '{}' or name contains '{}') and trashed = false".format(folderID, filename, filenameOpt)).execute()
    items = results.get('files', [])

    if not items:
        print('Não foram encontrados arquivos.')
    else:
        for item in items:
            ids.append(item['id'] + '\n')
            names.append(item['name'] + '\n')


def main():
    print('Conectando ao Google Drive...')
    service = None
    service = auth(service)
    print('Conexão realizada com sucesso!')

    if(len(sys.argv) > 1):
        if sys.argv[1].casefold() == 'firstrun':
            print('Google drive autorizado!')
        elif sys.argv[1].casefold() == 'save':
            print('Salvando arquivo no drive')
            fileUpload(service, sys.argv[2],
                       sys.argv[3], 'text/xml', CAACFolder)
            print('Arquivo gravado com sucesso!')
        elif sys.argv[1].casefold() == 'find':
            print('Buscando arquivos no drive...')
            ids = []
            searchFiles(100, service, sys.argv[2], ids)
            # save txt file
            txtFile = open('foundIDs.txt', 'w')
            txtFile.writelines(ids)
            txtFile.close()
        elif sys.argv[1].casefold() == 'listinfolder':
            print('Buscando arquivos na pasta AvaliadorCAAC...')
            ids = []
            listFilesInFolder(service, CAACFolder, ids)
            # save txt file
            txtFile = open('foundIDs.txt', 'w')
            txtFile.writelines(ids)
            txtFile.close()
        elif sys.argv[1].casefold() == 'findinfolder':
            print('Buscando arquivos na pasta AvaliadorCAAC...')
            ids = []
            names = []
            searchFilesInFolder(service, CAACFolder, sys.argv[2], "", ids, names)
            # save txt files
            txtFile = open('foundIDs.txt', 'w')
            txtFile.writelines(ids)
            txtFile.close()
        elif sys.argv[1].casefold() == 'findinfolder2':
            print('Buscando arquivos na pasta AvaliadorCAAC...')
            ids = []
            names = []
            searchFilesInFolder(service, CAACFolder, sys.argv[2], sys.argv[3], ids, names)
            # save txt files
            txtFile = open('foundIDs.txt', 'w')
            txtFile.writelines(ids)
            txtFile.close()
            txtFile = open('foundNames.txt', 'w')
            txtFile.writelines(names)
            txtFile.close()
        elif sys.argv[1].casefold() == 'delete':
            print('Removendo arquivo...')
            fileRemove(service, sys.argv[2])
        elif sys.argv[1].casefold() == 'replace':
            print('Removendo arquivo anterior...')
            fileRemove(service, sys.argv[2])
            print('Salvando arquivo no drive')
            fileUpload(service, sys.argv[3],
                       sys.argv[4], 'text/xml', CAACFolder)
            print('Arquivo gravado com sucesso!')
        elif sys.argv[1].casefold() == 'download':
            fileDownload(service, sys.argv[2], sys.argv[3])

    return 1


if __name__ == "__main__":
    main()
