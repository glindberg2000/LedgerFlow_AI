#!/bin/bash

mkdir -p archives

rsync -av --exclude "__pycache__" --exclude "*.pyc" --exclude ".git" "../PDF-extractor/scripts/" "archives/scripts/"
rsync -av --exclude "__pycache__" --exclude "*.pyc" --exclude ".git" "../PDF-extractor/backups/" "archives/backups/"
rsync -av --exclude "__pycache__" --exclude "*.pyc" --exclude ".git" "../PDF-extractor/services/" "archives/services/"
