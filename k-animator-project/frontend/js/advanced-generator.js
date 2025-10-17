document.addEventListener('DOMContentLoaded', () => {
    // --- DOM 요소 가져오기 ---
    const form = document.querySelector('.settings-panel form');
    const promptTextarea = document.getElementById('prompt');
    const charCounter = document.querySelector('.char-counter');
    const submitButton = document.querySelector('.btn-submit');
    const displayPanel = document.querySelector('.panel.display-panel');
    const uploadBox = document.querySelector('.upload-box');
    const fileInput = document.querySelector('.file-input');

    // Terraform에 설정된 API Gateway 경로를 기반으로 URL 설정
    const API_BASE_URL = '/api/gpt'; 
    // 결과 조회 API는 별도의 경로를 가질 수 있으므로 따로 정의
    const RESULT_API_BASE_URL = '/api/gpt';

    /**
     * 오른쪽 이미지 표시 패널의 상태를 업데이트하는 함수
     * @param {'loading' | 'success' | 'error' | 'initial'} state - 현재 상태
     * @param {object | null} data - 상태에 따라 필요한 데이터 (e.g., 이미지 URL, 에러 메시지)
     */
    const updateDisplayPanel = (state, data = null) => {
        const resultContainer = displayPanel.querySelector('.display-header + div');
        let content = '';

        switch (state) {
            case 'loading':
                content = `
                    <div class="loading-spinner">
                        <div class="spinner"></div>
                        <p><b>이미지를 생성하고 있습니다...</b></p>
                        <p>잠시만 기다려 주세요. 최대 1~2분 소요될 수 있습니다.</p>
                    </div>
                `;
                break;
            case 'success':
                content = `
                    <div class="image-result-container">
                        <img src="${data.png_url}" alt="생성된 이미지" class="generated-image">
                        <div class="image-actions">
                            <a href="${data.png_url}" download="generated_image.png" class="btn btn-download">PNG 다운로드</a>
                            <a href="${data.psd_url}" download="generated_image.psd" class="btn btn-download">PSD 다운로드</a>
                        </div>
                    </div>
                `;
                break;
            case 'error':
                content = `
                    <div class="image-placeholder error">
                        <i class="fa-regular fa-circle-xmark"></i>
                        <p><b>이미지 생성에 실패했습니다</b></p>
                        <p>${data.error || '알 수 없는 오류가 발생했습니다. 다시 시도해 주세요.'}</p>
                    </div>
                `;
                break;
            default: // initial
                content = `
                    <div class="image-placeholder">
                        <i class="fa-regular fa-image"></i>
                        <p><b>아직 생성된 이미지가 없습니다</b></p>
                        <p>왼쪽 패널에서 설정을 완료하고 이미지를 생성해보세요</p>
                    </div>
                `;
        }
        resultContainer.innerHTML = content;
    };

    /**
     * 작업 ID를 사용하여 주기적으로 결과를 확인하는 함수 (폴링)
     * @param {string} taskId - 확인할 Celery 작업 ID
     */
    const pollForResult = (taskId) => {
        const pollInterval = 4000; 
        const maxAttempts = 45;   
        let attempts = 0;

        const intervalId = setInterval(async () => {
            if (attempts >= maxAttempts) {
                clearInterval(intervalId);
                updateDisplayPanel('error', { error: '작업 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.' });
                submitButton.disabled = false;
                submitButton.textContent = '이미지 생성하기';
                return;
            }

            try {
                const response = await axios.get(`${RESULT_API_BASE_URL}/result/${taskId}`);
                const result = response.data;

                if (result.status === 'SUCCESS') {
                    clearInterval(intervalId);
                    updateDisplayPanel('success', result);
                    submitButton.disabled = false;
                    submitButton.textContent = '이미지 생성하기';
                } else if (result.status === 'FAILURE') {
                    clearInterval(intervalId);
                    updateDisplayPanel('error', { error: response.data.detail || '작업 실패' });
                    submitButton.disabled = false;
                    submitButton.textContent = '이미지 생성하기';
                }
        
            } catch (error) {
                console.error('결과 폴링 중 오류 발생:', error);
                clearInterval(intervalId);
                const errorMessage = error.response?.data?.detail || '결과를 가져오는 중 오류가 발생했습니다.';
                updateDisplayPanel('error', { error: errorMessage });
                submitButton.disabled = false;
                submitButton.textContent = '이미지 생성하기';
            }
            attempts++;
        }, pollInterval);
    };

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const prompt = promptTextarea.value.trim();

        if (!prompt) {
            alert('프롬프트를 입력해주세요.');
            return;
        }

        submitButton.disabled = true;
        submitButton.textContent = '생성 중...';
        updateDisplayPanel('loading');

        try {
            const response = await axios.post(`${API_BASE_URL}/generate-image`, {
                text_prompt: prompt,
                image_url: null 
            });

            const { task_id } = response.data;

            if (task_id) {
                pollForResult(task_id);
            } else {
                throw new Error('Task ID를 받지 못했습니다.');
            }
        } catch (error) {
            console.error('생성 요청 실패:', error);
            const errorMessage = error.response?.data?.detail || 'API 요청에 실패했습니다. 서버 상태를 확인해주세요.';
            updateDisplayPanel('error', { error: errorMessage });
            submitButton.disabled = false;
            submitButton.textContent = '이미지 생성하기';
        }
    });

    promptTextarea.addEventListener('input', () => {
        const count = promptTextarea.value.length;
        charCounter.textContent = `${count}/500`;
    });

    uploadBox.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files && fileInput.files[0]) {
            const reader = new FileReader();
            reader.onload = (e) => {
                uploadBox.innerHTML = `<img src="${e.target.result}" alt="참조 이미지 미리보기" class="image-preview">`;
            }
            reader.readAsDataURL(fileInput.files[0]);
        }
    });
});

