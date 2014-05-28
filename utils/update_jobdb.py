from pymongo import MongoClient
from gridfs import GridFS
from pathlib import Path
import json
from io import BytesIO
import zipfile


def main():
    client = MongoClient()
    db = client.snakeflow
    fs = GridFS(db, collection='workflows')
    wfs = db.workflows

    for dir in (p for p in Path().iterdir() if p.is_dir()):
        if not (dir / "meta.json").exists():
            print("Not a cluster job:" + str(dir))
            continue
        with (dir / "meta.json").open() as f:
            meta = json.load(f)
        old = wfs.find_one({'name': meta['name'], 'version': meta['version']})
        if old is not None:
            print("Not changed: " + str(dir))
            continue
        with (dir / "webview.js").open('rb') as f:
            html = f.read()
        zip = BytesIO()
        with zipfile.ZipFile(zip, 'w') as zip_file:
            zip_file.write(str(dir))

        grid_zip = fs.new_file()
        with client.start_request():
            grid_zip.write(zip.getvalue())
            grid_zip.close()

        grid_html = fs.new_file()
        with client.start_request():
            grid_html.write(html)
            grid_html.close()

        meta['_files'] = {
            'zipfile': grid_zip._id,
            'webview': grid_html._id,
        }

        wfs.insert(meta)


if __name__ == '__main__':
    main()
