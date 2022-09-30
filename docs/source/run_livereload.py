from livereload import Server, shell

if __name__ == '__main__':
    build_cmd = 'make.bat html'
    server = Server()
    server.watch('*.rst', shell(build_cmd), delay=1)
    server.watch('modules/*.rst', shell(build_cmd), delay=1)
    server.watch('*.py', shell(build_cmd), delay=1)
    server.watch('../../bookmarks/**', shell(build_cmd), delay=1)
    server.watch('_static/*', shell(build_cmd), delay=1)
    server.watch('_templates/*', shell(build_cmd), delay=1)
    server.serve(root='../build/html')
