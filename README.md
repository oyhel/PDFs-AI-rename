# PDFs-AI-rename

#How to use this script

## Install poppler (to convert PDFs to PNGs)
On windows easiest to download the latest binaries packaged by
[oschwartz10612](https://github.com/oschwartz10612/poppler-windows) on GitHub.

1. Download the latest release copy contents to e.g.: C:\Program Files\

2. Add the bin to PATH variable.
 - Press windows key -->  "Edit environment variables for your account"
 - Double click Path --> new --> add e.g. C:\Program Files\poppler-25.07.0\Library\bin
 - Restart Terminal and make sure pdfinfo (or other binary in bin) works.

## Install uv package manager
Install instructions here: https://docs.astral.sh/uv/getting-started/installation/

## To run the script
- Clone the repo
```
git clone git@github.com:oyhel/PDFs-AI-rename.git
```

Run the script with
uv run .\pdfs_ai_rename_pngonly.py



