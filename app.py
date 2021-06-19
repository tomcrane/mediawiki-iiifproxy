import requests
import flask
import json
from flask import Flask, redirect
from flask_cors import CORS
from html_sanitizer import Sanitizer
from iiif_prezi.factory import ManifestFactory, ImageService

app = Flask(__name__)
CORS(app)

COMMONS_TEMPLATE = u"https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=imageinfo&iiprop=" \
                   u"url|timestamp|user|mime|extmetadata&iiurlwidth={0}&titles={1}"
HEADERS = {'user-agent': 'iiif_test (tom.crane@digirati.com)'}
sanitizer = Sanitizer({
    'tags': {
        'a', 'b', 'br', 'i', 'img', 'p', 'span'
    },
    'attributes': {
        'a': ('href'),
        'img': ('src', 'alt')
    },
    'empty': {'br'},
    'separate': {'a', 'p'}
})
WIKI_SIZES = [320, 640, 800, 1024, 1280, 2560]
THUMB_TEMPLATE = "https://upload.wikimedia.org/wikipedia/commons/thumb/{0}/{1}/{2}/{3}px-{2}"
FULL_TEMPLATE = "https://upload.wikimedia.org/wikipedia/commons/{0}/{1}/{2}"


def sanitise(html):
    return sanitizer.sanitize(str(html))


@app.route('/<path:path>')
def any_path(path):
    if path.startswith("https://commons.wikimedia.org/"):
        file = path.split('/')[-1]
        return redirect(f'/presentation/{file}')


@app.route('/image/<p1>/<p2>/<file>')
def image_base(p1, p2, file):
    return redirect(flask.url_for('image_info', p1=p1, p2=p2, file=file))


@app.route('/image/<p1>/<p2>/<file>/info.json')
def image_info(p1, p2, file):
    large_images = get_image_details(f"File:{file}", 30000)
    for image_page in list(large_images.values()):
        wiki_info = image_page.get('imageinfo', [None])[0]
        if wiki_info is not None and wiki_info['mime'] == "image/jpeg":
            height = wiki_info['thumbheight']
            width = wiki_info['thumbwidth']
            image_service = make_image_service(p1, p2, file, height, width)
            return flask.jsonify(image_service)
    flask.abort(404)


@app.route('/image/<p1>/<p2>/<file>/full/<wh>/0/default.jpg')
def image_api_request(p1, p2, file, wh):
    width = int(wh.split(',')[0])
    if width > max(WIKI_SIZES):
        return redirect(FULL_TEMPLATE.format(p1, p2, file))
    else:
        return redirect(THUMB_TEMPLATE.format(p1, p2, file, width))
    abort(404)


def get_image_details(titles, size):
    titles = titles.replace('?', '%3F')
    url = COMMONS_TEMPLATE.format(str(size), titles)
    resp = requests.get(url, headers=HEADERS)
    return resp.json().get('query', {}).get('pages', {})


@app.route('/presentation/<file>')
def iiif_file_manifest(file):
    large_images = get_image_details(file, 30000)
    image_pages = list(large_images.values())
    thumbnail_images = get_image_details(file, 100)
    manifest = make_manifest_json(image_pages, thumbnail_images, file)
    return flask.jsonify(manifest)


def make_manifest_json(image_pages, thumbnail_images, file):
    file_name = file
    if file.startswith('File:'):
        file_name = file[5:]
    identifier = flask.url_for('iiif_file_manifest', file=file, _external=True)
    fac = ManifestFactory()
    fac.set_base_prezi_uri(flask.url_for('iiif_file_manifest', file='', _external=True))
    fac.set_debug("error")
    manifest = fac.manifest(ident=identifier, label=image_pages[0]['title'])
    sequence = manifest.sequence(ident="normal", label="default order")
    image_service = None
    for image_page in image_pages:
        page_id = image_page.get('pageid', None)
        wiki_info = image_page.get('imageinfo', [None])[0]
        if wiki_info is not None and wiki_info['mime'] == "image/jpeg":
            height = wiki_info['thumbheight']
            width = wiki_info['thumbwidth']
            canvas = sequence.canvas(ident=f'c{page_id}', label=image_page['title'])
            canvas.set_hw(height, width)
            set_canvas_metadata(wiki_info, canvas)
            anno = canvas.annotation(ident=f'a{page_id}')
            large_url = wiki_info['thumburl']
            large_url_parts = large_url.split('/')
            img = anno.image(ident=large_url, iiif=False)
            img.set_hw(height, width)
            image_service = make_image_service(large_url_parts[-3], large_url_parts[-2], file_name, height, width)
            thumb_page = thumbnail_images.get(str(page_id), None)
            if thumb_page is not None:
                thumb_info = thumb_page['imageinfo'][0]
                canvas.thumbnail = fac.image(ident=thumb_info['thumburl'])
                canvas.thumbnail.format = "image/jpeg"
                canvas.thumbnail.set_hw(thumb_info['thumbheight'], thumb_info['thumbwidth'])
    j_manifest = manifest.toJSON(top=True)
    j_manifest["sequences"][0]["canvases"][0]["images"][0]["resource"]["service"] = image_service
    return j_manifest


def make_image_service(p1, p2, file, height, width):
    sizes = []
    for w_width in WIKI_SIZES:
        if w_width < width:
            sizes.append({
                "width": w_width,
                "height": int(height*(w_width/width))
            })
    sizes.append({
        "width": width,
        "height": height
    })
    return {
      "@context": "http://iiif.io/api/image/2/context.json",
      "@id": flask.url_for('image_base', p1=p1, p2=p2, file=file, _external=True),
      "protocol": "http://iiif.io/api/image",
      "width": width,
      "height": height,
      "profile": ["http://iiif.io/api/image/2/level0.json"],
      "sizes": sizes
    }


def set_canvas_metadata(wiki_info, canvas):
    if 'user' in wiki_info:
        canvas.set_metadata({"Wikipedia user": wiki_info['user']})
        extmetadata = wiki_info.get('extmetadata', {})
    for key in extmetadata:
        value = extmetadata[key].get('value', None)
        if key == "LicenseUrl":
            canvas.license = value
        if key == "ImageDescription":
            canvas.label = sanitise(value)
        elif value:
            canvas.set_metadata({key: sanitise(value)})


if __name__ == '__main__':
    app.run()
