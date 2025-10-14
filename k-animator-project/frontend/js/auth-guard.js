const accessToken = localStorage.getItem('accessToken');

if (!accessToken) {
    alert('로그인이 필요합니다.');
    window.location.href = 'login-signup.html';
}