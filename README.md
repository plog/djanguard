# Docker
docker build -f Dockerfile.base -t plog/proctoring_base:0.1 .

# Django
```
python manage.py makemigrations proctoring 
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

python manage.py makemessages -l fr ; python manage.py makemessages -l id ; python manage.py makemessages -l en
```

## Testing background processes
python manage.py shell -c "from processing.tasks import process_sessions; process_sessions()"

# browser_extensions
https://github.com/dutiyesh/chrome-extension-cli/tree/master
Inside the newly created project, you can run some built-in commands:

### `npm run watch`

Runs the app in development mode.<br>
Then follow these instructions to see your app:
1. Open **chrome://extensions**
2. Check the **Developer mode** checkbox
3. Click on the **Load unpacked extension** button
4. Select the folder **my-extension/build**

### `npm run build`
Builds the app for production to the build folder.<br>
Run `npm run pack` to
zip the build folder and your app is ready to be published on Chrome Web Store.<br>
Or you can zip it manually.

### `npm run pack`
Packs the build folder into a zip file under release folder.

### `npm run repack`
Rebuilds and packs the app into a zip file.
It is a shorthand for `npm run build && npm run pack`.

### `npm run format`
Formats all the HTML, CSS, JavaScript, TypeScript and JSON files.

# Javascript Wavesurfer
https://wavesurfer.xyz/example/