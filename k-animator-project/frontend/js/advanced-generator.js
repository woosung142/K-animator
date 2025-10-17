document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('generation-form');
    const promptTextarea = document.getElementById('prompt');
    const charCounter = document.querySelector('.char-counter');
    const submitBtn = document.getElementById('submit-btn');
    const displayArea = document.getElementById('image-display-area');
    const fileInput = document.getElementById('file-input');
    const uploadBox = document.querySelector('.upload-box');
    const uploadIcon = uploadBox.querySelector('i');

    let uploadedFileAsBase64 = null;

    promptTextarea.addEventListener('input', updateCharCounter);
    form.addEventListener('submit', handleImageGenerationRequest);
    fileInput.addEventListener('change', handleFilePreview);

    function updateCharCounter() {
        const currentLength = promptTextarea.value.length;
        charCounter.textContent = `${currentLength}/500`;
    }

    function handleFilePreview(event) {
        const file = event.target.files[0];
        if (!file) {
            // Clear preview if no file is selected
            uploadedFileAsBase64 = null;
            const existingPreview = uploadBox.querySelector('.image-preview');
            if(existingPreview) existingPreview.remove();
            uploadIcon.style.display = 'block';
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            uploadedFileAsBase64 = e.target.result; // Save as base64
            
            // Display preview
            const existingPreview = uploadBox.querySelector('.image-preview');
            if(existingPreview) existingPreview.remove();
            
            const img = document.createElement('img');
            img.src = uploadedFileAsBase64;
            img.classList.add('image-preview');
            uploadBox.appendChild(img);
            uploadIcon.style.display = 'none';
        };
        reader.readAsDataURL(file);
    }
    
    async function handleImageGenerationRequest(event) {
        event.preventDefault();
        
        const prompt = promptTextarea.value.trim();
        if (!prompt) {
            alert('프롬프트를 입력해주세요.');
            return;
        }

        setLoadingState(true);

        try {
            // Step 1: Send the initial request to create the task
            const response = await axios.post('/api/generate-image', {
                text_prompt: prompt,
                image_url: uploadedFileAsBase64 // Can be null
            });

            const taskId = response.data.task_id;
            if (!taskId) {
                throw new Error('Task ID를 받지 못했습니다.');
            }
            
            // Step 2: Start polling for the result
            pollForResult(taskId);

        } catch (error) {
            console.error('Error starting generation task:', error);
            displayError('이미지 생성 시작에 실패했습니다. 잠시 후 다시 시도해주세요.');
            setLoadingState(false);
        }
    }

    /**
     * Polls the result endpoint until the task is complete or fails.
     * @param {string} taskId - The ID of the task to poll.
     */
    function pollForResult(taskId) {
        const pollInterval = 3000; // Poll every 3 seconds
        const maxPollTime = 120000; // Timeout after 2 minutes

        const intervalId = setInterval(async () => {
            try {
                const resultResponse = await axios.get(`/api/result/${taskId}`);
                const { status, result } = resultResponse.data;

                if (status === 'SUCCESS') {
                    clearInterval(intervalId);
                    clearTimeout(timeoutId);
                    displayResult(result);
                    setLoadingState(false);
                } else if (status === 'FAILURE') {
                    clearInterval(intervalId);
                    clearTimeout(timeoutId);
                    displayError(result?.error || '이미지 생성에 실패했습니다.');
                    setLoadingState(false);
                }

            } catch (error) {
                console.error('Error polling for result:', error);
                clearInterval(intervalId);
                clearTimeout(timeoutId);
                displayError('결과를 조회하는 중 오류가 발생했습니다.');
                setLoadingState(false);
            }
        }, pollInterval);

        const timeoutId = setTimeout(() => {
            clearInterval(intervalId);
            displayError('이미지 생성 시간이 초과되었습니다. 나중에 다시 시도해주세요.');
            setLoadingState(false);
        }, maxPollTime);
    }
    
    /**
     * Toggles the UI into a loading state.
     * @param {boolean} isLoading - True to show loading, false to hide.
     */
    function setLoadingState(isLoading) {
        submitBtn.disabled = isLoading;
        promptTextarea.disabled = isLoading;
        if (isLoading) {
            submitBtn.textContent = '생성 중...';
            displayArea.innerHTML = '<div class="loading-spinner"></div>';
        } else {
            submitBtn.textContent = '이미지 생성하기';
            promptTextarea.disabled = false;
        }
    }
    
    /**
     * Displays the generated image and download links.
     * @param {object} resultData - The result object containing png_url and psd_url.
     */
    function displayResult(resultData) {
        if (!resultData || !resultData.png_url) {
            displayError('유효하지 않은 결과 데이터입니다.');
            return;
        }

        displayArea.innerHTML = `
            <div class="result-container">
                <img src="${resultData.png_url}" alt="Generated Image" class="result-image">
                <div class="download-buttons">
                    <a href="${resultData.png_url}" class="btn-png" download>PNG 다운로드</a>
                    <a href="${resultData.psd_url}" class="btn-psd" download>PSD 다운로드</a>
                </div>
            </div>
        `;
    }

    /**
     * Displays an error message in the display area.
     * @param {string} message - The error message to display.
     */
    function displayError(message) {
        displayArea.innerHTML = `
            <div class="image-placeholder">
                <i class="fa-solid fa-circle-exclamation" style="color: var(--error-color);"></i>
                <p><b>오류 발생</b></p>
                <p>${message}</p>
            </div>
        `;
    }
});
