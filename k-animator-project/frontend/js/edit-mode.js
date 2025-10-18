document.addEventListener('DOMContentLoaded', () => {
    const imageDisplay = document.querySelector('.image-display img');

    // URL에서 'imageUrl' 쿼리 파라미터를 가져옵니다.
    const urlParams = new URLSearchParams(window.location.search);
    const imageUrl = urlParams.get('imageUrl');

    if (imageUrl) {
        // 디코딩된 URL을 이미지 src에 설정합니다.
        imageDisplay.src = decodeURIComponent(imageUrl);
        imageDisplay.alt = "편집할 이미지";
    } else {
        // 이미지 URL이 없는 경우, 에러 또는 플레이스홀더 처리
        imageDisplay.alt = "편집할 이미지를 불러오지 못했습니다.";
        // 필요하다면, 사용자에게 알림을 표시할 수 있습니다.
        console.error('Image URL not found in query parameters.');
    }
});
