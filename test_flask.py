import threading
from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello World"

if __name__ == "__main__":
    import time
    import urllib.request
    
    def client_task():
        import sys
        
        # Disable proxies for urllib
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        urllib.request.install_opener(opener)
        
        with open('test_out.txt', 'w') as f:
            f.write("Wait...\n")
            f.flush()
            time.sleep(2)
            for _ in range(3):
                try:
                    res = urllib.request.urlopen("http://127.0.0.1:5000", timeout=1)
                    f.write(f"OK: {res.read()}\n")
                    f.flush()
                    break
                except Exception as e:
                    f.write(f"Error: {e}\n")
                    f.flush()
                    time.sleep(1)
            f.write("Done loop.\n")
            f.flush()
        # Kill the flask server after test
        import os, signal
        os.kill(os.getpid(), signal.SIGTERM)

    t = threading.Thread(target=client_task)
    t.daemon = True
    t.start()
    
    app.run(port=5000, host='127.0.0.1', debug=False, use_reloader=False)
