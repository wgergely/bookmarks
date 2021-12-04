from livereload import Server, shell

if __name__ == '__main__':
    server = Server()
    server.watch('source/*.rst', shell('make.bat html'), delay=1)
    server.watch('source/*.py', shell('make.bat html'), delay=1)
    server.watch('../bookmarks/**', shell('make.bat html'), delay=1)
    server.watch('source/_static/*', shell('make.bat html'), delay=1)
    server.watch('source/_templates/*', shell('make.bat html'), delay=1)
    server.serve(root='build/html')