# mediawiki-iiifproxy

Exposes Wikimedia images as Level 0 IIIF Image API Services.

## Examples

### Manifest

https://iiifmediawiki.herokuapp.com/presentation/File:Gustave_Courbet_-_A_Burial_at_Ornans_-_Google_Art_Project_2.jpg

### Image Service

https://iiifmediawiki.herokuapp.com/image/a/a0/Gustave_Courbet_-_A_Burial_at_Ornans_-_Google_Art_Project_2.jpg/info.json

### Image from Image Service

https://iiifmediawiki.herokuapp.com/image/a/a0/Gustave_Courbet_-_A_Burial_at_Ornans_-_Google_Art_Project_2.jpg/full/1024,470/0/default.jpg

Note that this then _redirects_ to the available Mediawiki size. But, we could proxy it instead.

### More

See https://github.com/tomcrane/scrapbook#technical-info-and-special-treatment-for-wikimedia for an example use.
