// 페이지 전환 애니메이션
const container = document.getElementById('container');

const toggle = () => {
    container.classList.toggle('sign-in');
    container.classList.toggle('sign-up');
};

// 페이지 로드 후 0.2초 뒤에 초기 상태(sign-in)를 설정하여 애니메이션이 보이도록 함
setTimeout(() => {
    container.classList.add('sign-in');
}, 200);

// 회원가입 API 연동
const signupButton = document.getElementById('signup-button');
const signupUsername = document.getElementById('signup-username');
const signupFullname = document.getElementById('signup-fullname');
const signupEmail = document.getElementById('signup-email');
const signupPassword = document.getElementById('signup-password');
const signupPasswordConfirm = document.getElementById('signup-password-confirm');

signupButton.addEventListener('click', async () => {
    const username = signupUsername.value;
    const fullname = signupFullname.value;
    const email = signupEmail.value;
    const password = signupPassword.value;
    const passwordConfirm = signupPasswordConfirm.value;
    
    // NOTE: alert() 대신 사용자 지정 모달 UI를 사용해야 합니다. 여기서는 디버깅을 위해 alert를 유지합니다.
    if (password !== passwordConfirm) {
        alert('비밀번호가 일치하지 않습니다.');
        return;
    }

    if (!username || !fullname || !email || !password) {
        alert('모든 필드를 채워주세요.');
        return;
    }

    try {
        // [수정: Axios 경로] 맨 앞의 슬래시(/) 제거 (상대 경로로 인식하여 baseURL에 연결)
        const response = await api.post('/api/auth/signup', { 
            "username": username,
            "email": email,
            "full_name": fullname,
            "password": password
        });

        // Axios는 2xx 응답 시에만 try 블록을 실행하며, 데이터는 response.data에 있습니다.
        if (response.status === 201) { // 201 Created 확인
            const data = response.data;
            console.log('회원가입 성공:', data);
            alert('회원가입에 성공했습니다! 이제 로그인 해주세요.');
            toggle(); // 성공 시 로그인 창으로 자동 전환
        }

    } catch (error) {
        // Axios 오류는 catch 블록으로 들어오며, error.response에 상세 정보가 있습니다.
        const errorResponse = error.response;
        if (errorResponse && errorResponse.data) {
             // detail 메시지 파싱 로직은 그대로 유지
             const detail = errorResponse.data.detail || '알 수 없는 오류';
             alert(`회원가입 실패 (${errorResponse.status}): ${detail}`);
             console.error('Axios Error Response:', errorResponse);
        } else {
            alert('서버와 통신 중 오류가 발생했습니다.');
            console.error('Axios Fetch Error:', error);
        }
    }
});

// 로그인 API 연동
const signinButton = document.getElementById('signin-button');
const signinUsername = document.getElementById('signin-username');
const signinPassword = document.getElementById('signin-password');

signinButton.addEventListener('click', async () => {
    const username = signinUsername.value;
    const password = signinPassword.value;

    // --- [핵심 수정: 422 오류 방지를 위한 유효성 검사 추가] ---
    if (!username.trim() || !password.trim()) {
        alert('사용자 이름과 비밀번호를 모두 입력해야 합니다.');
        console.error('Validation Error: Missing username or password.');
        return;
    }
    // -----------------------------------------------------------------

    const loginData = { 
        "username": username,
        "password": password
    };
    console.log("서버로 전송할 JSON 본문:", loginData);
    
    try {
        // [수정: Axios 경로] 맨 앞의 슬래시(/) 제거 (상대 경로로 인식하여 baseURL에 연결)
        const response = await api.post('/api/auth/login', loginData); 


        // Axios는 2xx 응답 시에만 try 블록을 실행합니다.
        // 데이터는 response.data에 들어있습니다.
        const data = response.data;
        console.log('로그인 성공:', data);
        localStorage.setItem('accessToken', data.access_token);
        window.location.href = 'basic-generator.html';

    } catch (error) {
        // Axios 오류는 catch 블록으로 들어오며, error.response에 상세 정보가 있습니다.
        const errorResponse = error.response;
        
        if (errorResponse) {
            const status = errorResponse.status;
            const errorData = errorResponse.data;
            
            console.error('로그인 실패 (응답 데이터):', errorData, `Status: ${status}`); 
            
            let errorMessage = `로그인 실패: 입력 내용을 확인해주세요. (${status})`;

            if (status === 401 && errorData.detail) {
                // FastAPI 401 오류 메시지 처리
                errorMessage = `로그인 실패: ${errorData.detail} (${status})`;
            } else if (status === 422 && errorData.detail && Array.isArray(errorData.detail) && errorData.detail.length > 0) {
                // FastAPI 422 Unprocessable Entity 에러 처리 (FastAPI 상세 에러 파싱)
                 const errorDetail = errorData.detail[0];
                 const loc = errorDetail.loc.length > 1 ? errorDetail.loc[1] : '필드';
                 errorMessage = `로그인 실패: [${loc}] - ${errorDetail.msg} (${status})`;
            } else if (errorData.detail) {
                // 기타 detail 메시지
                 errorMessage = `로그인 실패: ${errorData.detail} (${status})`;
            }
            
            alert(errorMessage);
        } else {
            // 서버 연결 실패, 네트워크 오류 등
            alert('서버와 통신 중 오류가 발생했습니다. 네트워크 연결 상태를 확인해주세요.');
            console.error('Axios Fetch Error:', error);
        }
    }
});
