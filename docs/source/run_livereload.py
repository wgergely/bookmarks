from livereload import Server, shell

if __name__ == '__main__':
    server = Server()
    server.watch('*.rst', shell('make.bat html'), delay=1)
    server.watch('api/*.rst', shell('make.bat html'), delay=1)
    server.watch('*.py', shell('make.bat html'), delay=1)
    server.watch('../../bookmarks/**', shell('make.bat html'), delay=1)
    server.watch('_static/*', shell('make.bat html'), delay=1)
    server.watch('_templates/*', shell('make.bat html'), delay=1)
    server.serve(root='../html')