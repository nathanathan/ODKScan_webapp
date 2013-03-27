This code is for generating paper forms from XLS spreadsheets.

[Documentation](https://code.google.com/p/opendatakit/wiki/ScanXLSFormDocumentation)

# Dependencies

xlrd

```bash
sudo pip install -r requirements.pip
```

# Maintenance

Forms are stored in the `/tmp` directory, and may need to be periodically removed to free up disk space.
This doesn't need to happen very often. AWS instances come with an ~8GB drive mounted.
[tmpreaper](http://manpages.ubuntu.com/manpages/hardy/man8/tmpreaper.8.html>) can be used to remove older forms that are unlikely to be accessed.

