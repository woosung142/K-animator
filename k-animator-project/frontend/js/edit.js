document.addEventListener('DOMContentLoaded', async () => {
    const imageGrid = document.querySelector('.image-grid');
    const imageCountSpan = document.querySelector('.gallery-header span');

    if (!imageGrid || !imageCountSpan) {
        console.error('필수 HTML 요소(.image-grid 또는 .gallery-header span)를 찾을 수 없습니다.');
        return;
    }

    // 기존 플레이스홀더 내용 지우기
    imageGrid.innerHTML = '<p>이미지를 불러오는 중...</p>';

    try {
        const response = await api.get('/api/utils/my-images');
        const images = response.data;

        imageGrid.innerHTML = ''; // 로딩 메시지 제거

        if (images.length === 0) {
            imageCountSpan.textContent = '총 0개';
            imageGrid.innerHTML = '<p>생성한 이미지가 없습니다.</p>';
            return;
        }

        imageCountSpan.textContent = `총 ${images.length}개`;

        images.forEach(image => {
            const linkElement = document.createElement('a');
            // 각 이미지를 클릭하면 imageId를 가지고 edit-mode.html로 이동
            linkElement.href = `edit-mode.html?imageId=${image.id}`;
            linkElement.className = 'image-link';

            const cardElement = document.createElement('div');
            cardElement.className = 'image-card';

            const imgElement = document.createElement('img');
            imgElement.src = image.url;
            imgElement.alt = image.prompt || '생성된 이미지';

            cardElement.appendChild(imgElement);
            linkElement.appendChild(cardElement);
            imageGrid.appendChild(linkElement);
        });

    } catch (error) {
        console.error('이미지 목록 조회 실패:', error);
        imageGrid.innerHTML = '<p>이미지를 불러오는 데 실패했습니다. 페이지를 새로고침 해주세요.</p>';
        if (error.response && error.response.status === 401) {
            // 인증 오류 시 로그인 페이지로
            window.location.href = 'login-signup.html';
        }
    }
});
