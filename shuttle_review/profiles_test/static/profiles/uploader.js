// Modern drag-and-drop multi-file uploader for StatementFile

document.addEventListener('DOMContentLoaded', function () {
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('id_files');
    const uploadForm = document.getElementById('statement-upload-form');
    const progressContainer = document.getElementById('progress-container');
    const clientSelect = document.getElementById('id_client');
    const fileTypeSelect = document.getElementById('id_file_type');

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Highlight drop area
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => dropArea.classList.add('highlight'), false);
    });
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => dropArea.classList.remove('highlight'), false);
    });

    // Handle dropped files
    dropArea.addEventListener('drop', handleDrop, false);
    function handleDrop(e) {
        let dt = e.dataTransfer;
        let files = dt.files;
        fileInput.files = files;
        showFiles(files);
    }

    // Show selected files
    fileInput.addEventListener('change', function () {
        showFiles(fileInput.files);
    });

    function showFiles(files) {
        progressContainer.innerHTML = '';
        for (let i = 0; i < files.length; i++) {
            let file = files[i];
            let div = document.createElement('div');
            div.className = 'file-progress';
            div.innerHTML = `<span>${file.name}</span> <progress value="0" max="100"></progress>`;
            progressContainer.appendChild(div);
        }
    }

    // AJAX upload
    uploadForm.addEventListener('submit', function (e) {
        e.preventDefault();
        let files = fileInput.files;
        if (!files.length) return;
        let client = clientSelect.value;
        let fileType = fileTypeSelect.value;
        for (let i = 0; i < files.length; i++) {
            uploadFile(files[i], client, fileType, i);
        }
    });

    function uploadFile(file, client, fileType, idx) {
        let url = uploadForm.action;
        let formData = new FormData();
        formData.append('client', client);
        formData.append('file_type', fileType);
        formData.append('files', file);
        formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);
        let xhr = new XMLHttpRequest();
        xhr.open('POST', url, true);
        xhr.upload.addEventListener('progress', function (e) {
            if (e.lengthComputable) {
                let percent = (e.loaded / e.total) * 100;
                progressContainer.children[idx].querySelector('progress').value = percent;
            }
        });
        xhr.onload = function () {
            if (xhr.status === 200) {
                progressContainer.children[idx].querySelector('progress').value = 100;
                progressContainer.children[idx].classList.add('success');
            } else {
                progressContainer.children[idx].classList.add('error');
            }
        };
        xhr.send(formData);
    }
}); 