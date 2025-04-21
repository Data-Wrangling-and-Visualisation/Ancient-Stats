from flask import Flask, request, jsonify
from flask_cors import CORS
from requests import get

app = Flask(__name__)
CORS(app)


@app.route('/')
def index():
    args = {**request.args}
    print(args)
    if 'hero_id' in args:
        return get(f'http://localhost:8080/stats/{args.pop("hero_id")}', args).json()
    else:
        return get('http://localhost:8080/stats/', args).json()


if __name__ == '__main__':
    app.run(threaded=True)
