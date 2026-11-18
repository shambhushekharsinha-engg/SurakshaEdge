path = 'C:/SurakshaEdge/surakshaedge/api/main.py'
content = open(path, encoding='utf-8').read()
# Fix the escaped-quote issue on the @app.get("/health") line
fixed = content.replace('@app.get(\\"/health\\")', '@app.get("/health")')
open(path, 'w', encoding='utf-8').write(fixed)
print('Fixed:', '@app.get("/health")' in fixed)
