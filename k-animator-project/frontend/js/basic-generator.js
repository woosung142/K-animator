// DOM 요소 가져오기
const userProfileBtn = document.getElementById('user-profile-btn');
const userProfileModal = document.getElementById('user-profile-modal');
const closeProfileBtn = document.getElementById('close-profile-btn');
const logoutBtn = document.getElementById('logout-btn');

const profileUsername = document.getElementById('profile-username');
const profileFullname = document.getElementById('profile-fullname');
const profileEmail = document.getElementById('profile-email');

// APIM 구독 키는 api.js에 설정되어 있으므로, 여기서는 신경 쓰지 않습니다.

/**
 * 사용자 프로필 데이터를 백엔드에서 가져와 모달에 표시합니다.
 */
async function fetchAndDisplayUserProfile() {
    // 로딩 상태 표시
    profileUsername.textContent = '로딩 중...';
    profileFullname.textContent = '로딩 중...';
    profileEmail.textContent = '로딩 중...';

    try {
        // '/api/users/me' 엔드포인트는 Access Token을 요구하며, 
        // api.js의 인터셉터가 자동으로 Authorization 헤더를 추가합니다.
        const response = await api.get('/api/users/me');
        const user = response.data;

        // 데이터 표시
        profileUsername.textContent = user.username;
        profileFullname.textContent = user.full_name;
        profileEmail.textContent = user.email;

    } catch (error) {
        console.error('사용자 프로필 조회 실패:', error);
        
        let errorMessage = '프로필 정보를 가져오는 데 실패했습니다.';
        if (error.response && error.response.status === 401) {
             errorMessage = '인증이 만료되었습니다. 다시 로그인해주세요.';
        } else if (error.response && error.response.data && error.response.data.detail) {
             errorMessage = `프로필 조회 실패: ${error.response.data.detail}`;
        }
        
        // 에러 메시지 표시
        profileUsername.textContent = '오류 발생';
        profileFullname.textContent = errorMessage;
        profileEmail.textContent = '---';

        // 401이면 로그인 페이지로 리다이렉트 (auth-guard.js에서 처리할 수도 있습니다)
        if (error.response && error.response.status === 401) {
             localStorage.removeItem('accessToken');
             window.location.href = 'index.html'; 
        }
    }
}

/**
 * 사용자 프로필 모달을 열고 사용자 데이터를 가져옵니다.
 */
userProfileBtn.addEventListener('click', () => {
    userProfileModal.classList.add('active');
    fetchAndDisplayUserProfile();
});

/**
 * 사용자 프로필 모달을 닫습니다.
 */
closeProfileBtn.addEventListener('click', () => {
    userProfileModal.classList.remove('active');
});

/**
 * 로그아웃 처리 함수입니다.
 */
logoutBtn.addEventListener('click', async () => {
    try {
        // 백엔드의 로그아웃 엔드포인트 호출
        // 이 요청은 쿠키에 담긴 Refresh Token을 삭제합니다.
        const response = await api.post('/api/users/logout');
        
        if (response.status === 200) {
            // 로컬 스토리지의 Access Token 제거 및 로그인 페이지로 리다이렉트
            localStorage.removeItem('accessToken');
            alert('성공적으로 로그아웃되었습니다.');
            window.location.href = 'index.html';
        }

    } catch (error) {
        // 로그아웃 자체는 서버에서 리프레시 토큰만 지우면 되므로, 
        // 오류 발생 시에도 클라이언트 측에서는 강제 로그아웃을 진행하는 것이 안전합니다.
        console.error('로그아웃 요청 실패:', error);
        localStorage.removeItem('accessToken');
        alert('로그아웃 처리 중 오류가 발생했습니다. 강제 로그아웃됩니다.');
        window.location.href = 'index.html';
    }
});


// 기타 생성기 관련 로직은 여기에 추가될 수 있습니다.
const generateButton = document.getElementById('generate-button');
if (generateButton) {
    generateButton.addEventListener('click', () => {
        console.log('이미지 생성 버튼이 클릭되었습니다.');
        // 여기에 이미지 생성 API 호출 로직을 구현합니다.
    });
}

// ===================================================================================
// 추가된 기능들
// ===================================================================================

// 1. STT (Speech-to-Text) 기능
// -----------------------------------------------------------------------------------
const sttButton = document.getElementById('stt-btn');
const promptInput = document.getElementById('description');

if (sttButton && promptInput) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
        const recognition = new SpeechRecognition();
        recognition.lang = 'ko-KR';
        recognition.continuous = false;
        recognition.interimResults = false;

        sttButton.addEventListener('click', () => {
            sttButton.textContent = '음성 인식 중...';
            sttButton.disabled = true;
            recognition.start();
        });

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            promptInput.value = transcript;
        };

        recognition.onerror = (event) => {
            console.error('음성 인식 오류:', event.error);
            alert('음성 인식 중 오류가 발생했습니다.');
        };

        recognition.onend = () => {
            sttButton.textContent = '음성으로 입력';
            sttButton.disabled = false;
        };

    } else {
        sttButton.style.display = 'none';
        console.warn('이 브라우저는 음성 인식을 지원하지 않습니다.');
    }
}


// 2. 내 정보 수정 (이름)
// -----------------------------------------------------------------------------------
const editProfileBtn = document.getElementById('edit-profile-btn');
const saveProfileBtn = document.getElementById('save-profile-btn');

if (editProfileBtn && saveProfileBtn && profileFullname) {
    editProfileBtn.addEventListener('click', () => {
        profileFullname.contentEditable = true;
        profileFullname.focus();
        editProfileBtn.style.display = 'none';
        saveProfileBtn.style.display = 'inline-block';
    });

    saveProfileBtn.addEventListener('click', async () => {
        const newFullName = profileFullname.textContent;
        try {
            await api.patch('/api/users/me', { full_name: newFullName });
            alert('이름이 성공적으로 변경되었습니다.');
            profileFullname.contentEditable = false;
            saveProfileBtn.style.display = 'none';
            editProfileBtn.style.display = 'inline-block';
        } catch (error) {
            console.error('이름 변경 실패:', error);
            alert('이름 변경에 실패했습니다.');
            // 원래 이름으로 되돌릴 수 있도록 다시 프로필 정보를 불러옵니다.
            fetchAndDisplayUserProfile(); 
        }
    });
}


// 3. 비밀번호 변경
// -----------------------------------------------------------------------------------
const changePasswordBtn = document.getElementById('change-password-btn');
const changePasswordModal = document.getElementById('change-password-modal');
const closeChangePasswordBtn = document.getElementById('close-change-password-btn');
const changePasswordForm = document.getElementById('change-password-form');

if (changePasswordBtn && changePasswordModal && closeChangePasswordBtn && changePasswordForm) {
    changePasswordBtn.addEventListener('click', () => {
        changePasswordModal.classList.add('active');
    });

    closeChangePasswordBtn.addEventListener('click', () => {
        changePasswordModal.classList.remove('active');
    });

    changePasswordForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const oldPassword = document.getElementById('old-password').value;
        const newPassword = document.getElementById('new-password').value;
        const confirmPassword = document.getElementById('confirm-password').value;

        if (newPassword !== confirmPassword) {
            alert('새 비밀번호가 일치하지 않습니다.');
            return;
        }

        try {
            await api.put('/api/users/me/password', {
                current_password: oldPassword,
                new_password: newPassword,
            });
            alert('비밀번호가 성공적으로 변경되었습니다.');
            changePasswordForm.reset();
            changePasswordModal.classList.remove('active');
        } catch (error) {
            console.error('비밀번호 변경 실패:', error);
            let errorMessage = '비밀번호 변경에 실패했습니다.';
            if (error.response && error.response.data && error.response.data.detail) {
                errorMessage = `실패: ${error.response.data.detail}`;
            }
            alert(errorMessage);
        }
    });
}


// 4. 회원 탈퇴
// -----------------------------------------------------------------------------------
const deleteAccountBtn = document.getElementById('delete-account-btn');

if (deleteAccountBtn) {
    deleteAccountBtn.addEventListener('click', async () => {
        if (confirm('정말로 회원 탈퇴를 하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) {
            try {
                await api.delete('/api/users/me');
                alert('회원 탈퇴가 완료되었습니다. 이용해주셔서 감사합니다.');
                localStorage.removeItem('accessToken');
                window.location.href = 'index.html';
            } catch (error) {
                console.error('회원 탈퇴 실패:', error);
                alert('회원 탈퇴 처리 중 오류가 발생했습니다.');
            }
        }
    });
}


// 5. 내 이미지 목록 조회
// -----------------------------------------------------------------------------------
const myImagesBtn = document.getElementById('my-images-btn');
const myImagesModal = document.getElementById('my-images-modal');
const closeMyImagesBtn = document.getElementById('close-my-images-btn');
const myImagesContainer = document.getElementById('my-images-container');

if (myImagesBtn && myImagesModal && closeMyImagesBtn && myImagesContainer) {
    myImagesBtn.addEventListener('click', async () => {
        myImagesContainer.innerHTML = '<p>이미지를 불러오는 중...</p>';
        myImagesModal.classList.add('active');
        try {
            const response = await api.get('/api/images/me');
            const images = response.data;
            myImagesContainer.innerHTML = ''; // 기존 내용 초기화

            if (images.length === 0) {
                myImagesContainer.innerHTML = '<p>생성한 이미지가 없습니다.</p>';
                return;
            }

            images.forEach(image => {
                const imgElement = document.createElement('div');
                imgElement.className = 'my-image-item';
                imgElement.style.cursor = 'pointer'; // 클릭 가능함을 나타내는 커서 스타일
                imgElement.innerHTML = `
                    <img src="${image.url}" alt="user image">
                    <p>프롬프트: ${image.prompt || '없음'}</p>
                `;

                // 클릭 이벤트 리스너 추가
                imgElement.addEventListener('click', () => {
                    // API 응답에 id가 있다고 가정하고, edit.html로 이동
                    if (image.id) {
                        window.location.href = `edit.html?imageId=${image.id}`;
                    } else {
                        console.error('이미지 ID가 없어 편집 페이지로 이동할 수 없습니다.', image);
                        alert('이미지 정보가 올바르지 않아 편집 페이지로 이동할 수 없습니다.');
                    }
                });

                myImagesContainer.appendChild(imgElement);
            });

        } catch (error) {
            console.error('내 이미지 목록 조회 실패:', error);
            myImagesContainer.innerHTML = '<p>이미지를 불러오는 데 실패했습니다.</p>';
        }
    });

    closeMyImagesBtn.addEventListener('click', () => {
        myImagesModal.classList.remove('active');
    });
}
