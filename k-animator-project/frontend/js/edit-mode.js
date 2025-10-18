document.addEventListener('DOMContentLoaded', () => {
    const imageDisplay = document.querySelector('.image-display img');
    const separationBtn = document.getElementById('layer-separation-btn');
    const urlParams = new URLSearchParams(window.location.search);
    const imageUrl = urlParams.get('imageUrl');

    const API_BASE_URL = '/api/gpt'; // gptapi 서비스의 기본 경로

    // 1. 페이지 로드 시 이미지 표시
    if (imageUrl) {
        imageDisplay.src = decodeURIComponent(imageUrl);
        imageDisplay.alt = "편집할 이미지";
    } else {
        imageDisplay.alt = "편집할 이미지를 불러오지 못했습니다.";
        separationBtn.disabled = true;
        separationBtn.textContent = "이미지 없음";
        console.error('Image URL not found in query parameters.');
    }

    // 2. 레이어 분리 버튼 클릭 이벤트
    separationBtn.addEventListener('click', async () => {
        const currentImageUrl = imageDisplay.src;
        if (!currentImageUrl) {
            alert("편집할 이미지가 없습니다.");
            return;
        }

        separationBtn.disabled = true;
        separationBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 레이어 분리 중...';

        try {
            const response = await axios.post(`${API_BASE_URL}/separate-layers`, {
                image_url: currentImageUrl
            }, { withCredentials: true });

            const { task_id } = response.data;
            if (task_id) {
                pollForResult(task_id);
            } else {
                throw new Error('Task ID를 받지 못했습니다.');
            }
        } catch (error) {
            console.error('레이어 분리 요청 실패:', error);
            const errorMessage = error.response?.data?.detail || 'API 요청에 실패했습니다.';
            alert(`오류: ${errorMessage}`);
            separationBtn.disabled = false;
            separationBtn.innerHTML = '<i class="fa-solid fa-layer-group"></i> 레이어 분리 및 PSD 다운로드';
        }
    });

    // 3. 결과 폴링 함수
    const pollForResult = (taskId) => {
        const pollInterval = 5000; // 5초 간격
        const maxAttempts = 60;   // 5분 동안 시도
        let attempts = 0;

        const intervalId = setInterval(async () => {
            if (attempts >= maxAttempts) {
                clearInterval(intervalId);
                alert('작업 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.');
                separationBtn.disabled = false;
                separationBtn.innerHTML = '<i class="fa-solid fa-layer-group"></i> 레이어 분리 및 PSD 다운로드';
                return;
            }

            try {
                const response = await axios.get(`${API_BASE_URL}/result/${taskId}`, { withCredentials: true });
                const result = response.data;

                if (result.status === 'SUCCESS') {
                    clearInterval(intervalId);
                    alert('레이어 분리가 완료되었습니다! PSD 파일을 다운로드합니다.');
                    separationBtn.disabled = false;
                    separationBtn.innerHTML = '<i class="fa-solid fa-layer-group"></i> 레이어 분리 및 PSD 다운로드';
                    
                    // 다운로드 트리거
                    window.location.href = result.psd_layer_url;

                } else if (result.status === 'FAILURE') {
                    clearInterval(intervalId);
                    alert(`작업 실패: ${result.error || '알 수 없는 오류'}`);
                    separationBtn.disabled = false;
                    separationBtn.innerHTML = '<i class="fa-solid fa-layer-group"></i> 레이어 분리 및 PSD 다운로드';
                } else {
                    // PENDING 상태. 계속 폴링
                    console.log(`작업 상태: ${result.status}, 시도: ${attempts + 1}`)
                }
            } catch (error) {
                console.error('결과 폴링 중 오류 발생:', error);
                clearInterval(intervalId);
                const errorMessage = error.response?.data?.detail || '결과를 가져오는 중 오류가 발생했습니다.';
                alert(`오류: ${errorMessage}`);
                separationBtn.disabled = false;
                separationBtn.innerHTML = '<i class="fa-solid fa-layer-group"></i> 레이어 분리 및 PSD 다운로드';
            }
            attempts++;
        }, pollInterval);
    };
});