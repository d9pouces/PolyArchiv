# coding=utf-8
from polyarchiv.backends import HTTPRequestsStorageBackend
from polyarchiv.locals import LocalRepository

if __name__ == '__main__':
    repository = LocalRepository('name')
    backend = HTTPRequestsStorageBackend(repository, root_url='http://localhost:8008/')
    print('ls')
    print(backend.ls())
    print('ls')
    print(backend.ls('/images'))
    backend.sync_file_from_local(__file__, filename='demo.py')
    backend.sync_file_to_local('/tmp/test.py', filename='demo.py')
    print('walk')
    for data in backend.walk():
        print(data)
