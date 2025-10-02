// HTML에서 직접 호출해야 하므로 이 두 함수는 바깥에 둡니다.
function autoGrow(el) {
  if (!el) return;
  el.style.height = 'auto';
  const lineHeight = parseFloat(getComputedStyle(el).lineHeight);
  const maxLines = 6;
  const maxHeight = lineHeight * maxLines;
  const scrollHeight = el.scrollHeight;
  const newHeight = Math.min(scrollHeight, maxHeight);
  el.style.height = newHeight + 'px';
  el.style.overflowY = scrollHeight > maxHeight ? 'auto' : 'hidden';
}

function handleEnterSubmit(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    document.getElementById('generateImageBtn')?.click();
  }
}

// --- 페이지가 완전히 로드된 후 아래 코드를 실행합니다. ---
window.addEventListener('DOMContentLoaded', () => {

  // 모바일 기기인지 확인하여 스타일을 적용합니다.
  const isMobile = /Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
  if (isMobile) {
    document.body.classList.add('mobile');
    const left = document.getElementById('left-panel');
    if (left) {
      left.style.width = '100%';
      left.style.minWidth = '0';
      left.style.maxWidth = '100%';
    }
  }
  
  // 화면 크기에 따라 레이아웃을 조정하는 함수입니다.
  function adjustLayout() {
    const body = document.body;
    const left = document.getElementById('left-panel');
    const style = getComputedStyle(left);

    const minLeft = Math.ceil(parseFloat(style.minWidth || style.width));
    const minRight = 400;
    const gap = Math.ceil(parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--gap')) || 16);

    const totalNeeded = minLeft + minRight + gap;

    if (window.innerWidth < totalNeeded) {
        body.classList.add('stacked');
    } else {
        body.classList.remove('stacked');
    }
  }

  // 페이지 로드 시 및 창 크기 변경 시 레이아웃을 조정합니다.
  adjustLayout();
  window.addEventListener('resize', adjustLayout);
  
  // 초기 로드 시 캡션 입력창 높이를 조절합니다.
  const caption = document.getElementById('captionInput');
  autoGrow(caption);

  // --- 여기부터는 메인 애플리케이션 로직입니다. ---
  
  const qs = (sel, scope = document) => scope.querySelector(sel);
  const qsa = (sel, scope = document) => scope.querySelectorAll(sel);
  const on = (el, type, cb) => el.addEventListener(type, cb);
  const escapeHTML = str => str.replace(/[&<>"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));

  const chatbox = qs('#chatbox');
  const userInput = qs('#userInput');
  const form = qs('#chat-form');
  const sttBtn = qs('#sttBtn');
  const addFileBtn = qs('#addFileBtn');
  const fileInput = qs('#fileInput');
  const previewArea = qs('#preview-area');
  const generateImageBtn = qs('#generateImageBtn');
  const downloadPsdBtn = qs('#downloadPsdBtn');
  const openPsdBtn = qs('#openPsdBtn');
  const exeDownloadBtn = qs('#exeDownloadBtn');
  const captionInput = qs('#captionInput');
  const MAX_MB = 10;

  const categoryGroup = qs('#category-group');
  const layerGroup = qs('#layer-group');

  let generationStep = 'prompt';
  let currentTaskId = null;
  let fileToSend = null;
  let uploadedImageUrl = null;
  let psdUrl = null;
  let taskId = null;
  let recognizer = null;
  let selectedCategory = '';
  let selectedLayers = [];
  let pasteBlocked = false;
  let inputLocked = false; 
  let latestPsdData = null;

  let sessionId = sessionStorage.getItem('chatSessionId') || `web-user-${Date.now()}`;
  sessionStorage.setItem('chatSessionId', sessionId);

  document.addEventListener('paste', (e) => {
      if (pasteBlocked) {
          e.preventDefault();
      }
  });

  on(categoryGroup, 'click', e => {
      if (e.target.tagName !== 'BUTTON') return;
      qsa('button', categoryGroup).forEach(btn => btn.classList.remove('selected'));
      e.target.classList.add('selected');
      selectedCategory = e.target.dataset.value;
  });

  on(layerGroup, 'click', e => {
      if (e.target.tagName !== 'BUTTON') return;
      const buttons = layerGroup.querySelectorAll('button');
      for (let i = 0; i < buttons.length; i++) {
          buttons[i].classList.remove('selected');
      }
      e.target.classList.add('selected');
      selectedLayers = [e.target.dataset.value];
  });

  on(userInput, 'keydown', e => {
      if (e.key === 'Enter') {
          if (generateImageBtn.disabled) {
              e.preventDefault();
              return;
          }
          e.preventDefault();
          generateImageBtn.disabled = true;
          fileInput.disabled = true;
          pasteBlocked = true;
          userInput.readOnly = true;
          captionInput.readOnly = true;
          form.requestSubmit();
      }
  });

  on(generateImageBtn, 'click', () => {
      if (generateImageBtn.disabled) return;
      generateImageBtn.disabled = true;
      fileInput.disabled = true;
      pasteBlocked = true;
      userInput.readOnly = true;
      captionInput.readOnly = true;  
      form.requestSubmit();
  });

  const addLine = (who, content, isHtml = false, imageFile = null) => {
      const p = document.createElement('p');
      p.className = 'msg';
      p.innerHTML = `<strong>${who}:</strong> ${isHtml ? content : escapeHTML(content)}`;
      if (imageFile) {
          const reader = new FileReader();
          reader.onload = e => {
              const img = document.createElement('img');
              img.src = e.target.result;
              img.alt = '업로드 이미지 썸네일';
              img.style.maxWidth = '300px';
              img.style.marginTop = '0.5rem';
              p.appendChild(document.createElement('br'))
              p.appendChild(img);
              chatbox.appendChild(p);
              chatbox.scrollTop = chatbox.scrollHeight;
          };
          reader.readAsDataURL(imageFile);
      } else {
          chatbox.appendChild(p);
          chatbox.scrollTop = chatbox.scrollHeight;
      }
  };

  const showPreview = (file) => {
      fileToSend = file;
      const reader = new FileReader();
      reader.onload = (e) => {
          previewArea.innerHTML = `<img src="${e.target.result}" alt="미리보기"><button type="button" id="remove-preview-btn">×</button>`;
      };
      reader.readAsDataURL(file);
  };

  const clearPreview = () => {
      fileToSend = null;
      previewArea.innerHTML = '';
      fileInput.value = '';
  };

  on(previewArea, 'click', e => {
      if (e.target.id === 'remove-preview-btn') clearPreview();
  });

  on(addFileBtn, 'click', () => fileInput.click());

  on(fileInput, 'change', e => {
      if (fileToSend) {
          alert("이미 이미지가 첨부되어 있습니다. 기존 이미지를 제거하고 다시 시도하세요.");
          fileInput.value = '';
          return;
      }
      if (e.target.files && e.target.files.length > 0) {
          const file = e.target.files[0];
          if (file.size > MAX_MB * 1024 * 1024) {
              console.log('선택한 파일 크기:', file.size, 'bytes');
              alert("10MB 이하의 이미지만 업로드할 수 있습니다.");
              clearPreview();
              fileInput.value = "";  
              return;
          }
          if (!file.type.startsWith('image/')) {
              alert('이미지 파일만 업로드할 수 있습니다.');
              fileInput.value = '';
              clearPreview();
              return;
          }
          fileToSend = file; 
          showPreview(file);
      } else {
          clearPreview();
      }
  });

  on(captionInput, 'paste', e => {
      if (fileToSend) {
          alert("이미 이미지가 첨부되어 있습니다. 기존 이미지를 제거하고 다시 시도하세요.");
          return;
      }
      const items = (e.clipboardData || window.clipboardData).items;
      for (const item of items) {
          if (item.type.startsWith('image/')) {
              const file = item.getAsFile();
              if (file.size > MAX_MB * 1024 * 1024) {
                  console.log('선택한 파일 크기:', file.size, 'bytes');
                  alert("붙여넣은 이미지가 10MB를 초과합니다.");
                  return;
              }
              fileToSend = file; 
              showPreview(file);
              e.preventDefault();
              break;
          }
      }
  });

  const resetUI = () => {
      generationStep = 'prompt';
      currentTaskId = null;
      fileToSend = null;
      psdUrl = null;
      uploadedImageUrl = null;
      userInput.value = '';
      userInput.readOnly = false;
      captionInput.value = '';
      captionInput.readOnly = false;
      captionInput.placeholder = '장면 설명을 입력하세요';
      autoGrow(captionInput);
      qsa('.selection-btn').forEach(btn => btn.disabled = false);
      generateImageBtn.innerHTML = '▶';
      generateImageBtn.disabled = false;
      addFileBtn.disabled = false;
      fileInput.disabled = false;
      sttBtn.disabled = false;
      clearPreview();
  };

  on(form, 'submit', async (e) => {
      e.preventDefault();
      if (generationStep === 'prompt') {
          await handlePromptGeneration();
      } else if (generationStep === "image") {
          await handleImageGeneration();
      }
  });

  const handlePromptGeneration = async() => {
      const keywords = userInput.value.trim();
      const caption = captionInput.value.trim();

      if (!selectedCategory || selectedCategory === 0 || !keywords) {
          return alert("카테고리, 레이어, 키워드는 필수 입력 항목입니다.");
      }

      generateImageBtn.disabled = true;
      fileInput.disabled = true;
      pasteBlocked = true;
      userInput.readOnly = true;
      captionInput.readOnly = true;

      let userMessage = keywords;
      if (fileToSend) userMessage += ' (이미지 첨부)';
      if (caption) userMessage += `<br>(장면 설명: ${escapeHTML(caption)})`;
      addLine('나', userMessage, true, fileToSend);
      userInput.value = '';
      captionInput.value = '';
      autoGrow(captionInput)
      psdUrl = null;
      uploadedImageUrl = null;

      try {
          if (fileToSend) {
              addLine('시스템', '이미지를 업로드 중입니다...');
              const formData = new FormData();
              formData.append('image_file', fileToSend);
              const uploadRes = await fetch('/upload-image', {         // 변경된 부분 -> 배포 전 수정
                  method: 'POST',
                  body: formData
              });
              if (!uploadRes.ok) throw new Error('이미지 업로드 실패');
              const uploadResult = await uploadRes.json();
              if (!uploadResult.image_url) throw new Error('업로드 결과에 image_url이 없습니다.');
              uploadedImageUrl = uploadResult.image_url;
              clearPreview();
              fileToSend = null;
              addLine('시스템', '이미지 업로드 완료');
          }

          addLine('시스템', 'AI가 DALL-E 프롬프트를 생성 중입니다...');
          const res = await fetch('/api/generate-prompt', {        // 변경된 부분 -> 배포 전 수정
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                  category: selectedCategory,
                  layer: selectedLayers.join(', '),
                  tag: keywords,
                  caption_input: caption || null,
                  image_url: uploadedImageUrl || null
              })
          });
          console.log('[generate-image 요청 res]', res);
          if (!res.ok) throw new Error('이미지 생성 요청 실패');

          const { task_id } = await res.json();
          currentTaskId = task_id;
          checkStatus(currentTaskId, 'prompt');
      } catch (err) {
          console.error('[1단계 실패]', err);
          addLine('시스템', `⚠️ 요청 실패: ${err.message}`);
          resetUI();
      }
  };

  const handleImageGeneration = async () => {
      const finalPrompt = captionInput.value.trim();
      if(!finalPrompt) {
          return alert("DALL-E 프롬프트가 비어 있습니다.");
      }
      const messageContent = `
          (수정된 프롬프트로 이미지 생성 요청)
          <details class="prompt-details">
              <summary>수정된 프롬프트 보기 (클릭)</summary>
              <div class="prompt-content">${escapeHTML(finalPrompt)}</div>
          </details>
      `;
      addLine('나', messageContent, true);            
      addLine('시스템', '최종 이미지를 생성합니다. 잠시만 기다려주세요...');
      generateImageBtn.disabled = true;
      try {
          const res = await fetch('/api/generate-image-from-prompt', {     // 변경된 부분 -> 배포 전 수정
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                  dalle_prompt: finalPrompt
              })
          });
          if (!res.ok) throw new Error('최종 이미지 생성 요청 실패');
          const { task_id } = await res.json();
          currentTaskId = task_id;
          checkStatus(currentTaskId, 'image');
      } catch (err) {
          console.error('[2단계 실패]', err);
          addLine('시스템', `⚠️ 요청 실패: ${err.message}`);
          resetUI();
      }
  };

  const checkStatus = async (taskId, type) => {
      try {
          const resp = await fetch(`/api/result/${taskId}`);       // 변경된 부분 -> 배포 전 수정
          const result = await resp.json();
          if (result.status === 'PENDING') {
              setTimeout(() => checkStatus(taskId, type), 2000);
          } else if (result.status === 'SUCCESS') {
              if (type === 'prompt') {
                  const promptContent = `
                      <details class="prompt-details">
                          <summary>생성된 AI 프롬프트 보기 (클릭)</summary>
                          <div class="prompt-content">${escapeHTML(result.prompt)}</div>
                      </details>
                  `;
                  addLine('AI 프롬프트', promptContent, true);
                  captionInput.value = '';
                  captionInput.placeholder = '장면 설명을 입력하세요';
                  autoGrow(captionInput);
                  addLine('시스템', '프롬프트를 기반으로 바로 이미지를 생성합니다...');
                  try {
                      const res2 = await fetch('/api/generate-image-from-prompt', {        // 변경된 부분 -> 배포 전 수정
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ dalle_prompt: result.prompt })
                      });
                      if (!res2.ok) throw new Error('최종 이미지 생성 요청 실패');
                      const { task_id: newTaskId } = await res2.json();
                      currentTaskId = newTaskId;
                      checkStatus(currentTaskId, 'image');
                  } catch (err) {
                      console.error('[자동 이미지 생성 실패]', err);
                      addLine('시스템', `이미지 생성 실패: ${err.message}`);
                      resetUI();
                  }
              } else if (type === 'image') {
                  addLine('AI 이미지', `<img src="${result.png_url}" alt="생성된 이미지" style="width: 300px; height: 300px;">`, true);
                  addLine('다운로드', `<a href="${result.psd_url}" download>PSD 파일</a>`, true);
                  latestPsdData = {
                      url: result.psd_url,
                      taskId: taskId
                  };            
                  downloadPsdBtn.style.display = "inline-block";
                  openPsdBtn.style.display = "inline-block";
                  resetUI();
              }
              generateImageBtn.disabled = false;
              fileInput.disabled = false;
              pasteBlocked = false;
              userInput.readOnly = false;
              captionInput.readOnly = false;
          } else {
              throw new Error(result.detail || '알 수 없는 오류');
          }
      } catch (err) {
          console.error('[요청 실패]', err);
          addLine('시스템', `작업 처리 중 오류 발생: ${err.message}`);
      }
  };

  on(downloadPsdBtn, 'click', () => {
      if (!latestPsdData) {
          alert("다운로드 가능한 PSD 파일이 없습니다. 이미지를 먼저 생성해주세요.");
          return;
      }
      const a = document.createElement('a');
      a.href = latestPsdData.url;
      a.download = `${latestPsdData.taskId}.psd`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
  });

  on(openPsdBtn, 'click', async () => {
      if (!latestPsdData) {
          alert("실행할 PSD 파일이 없습니다. 이미지를 먼저 생성해주세요.");
          return;
      }
      try {
          await fetch("http://localhost:5001/download-and-open-psd", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ 
                url: latestPsdData.url, 
                filename: `${latestPsdData.taskId}.psd` })
          });
      } catch (err) {
          alert("실행기가 실행 중이 아니거나 통신에 실패했습니다. 설치 후 다시 시도해주세요.");
      }
  });

  on(exeDownloadBtn, 'click', () => {
      window.location.href = "https://user20storage.blob.core.windows.net/psd-download/psd_launcher.zip";
  });

  const initSpeech = async () => {
    resetUI();
    sttBtn.disabled = true;
    try {
        const response = await fetch('/get-speech-token');     // 변경된 부분 -> 배포 전 수정
        if (!response.ok) throw new Error('인증 토큰을 가져올 수 없습니다.');
        const data = await response.json();
        const speechConfig = SpeechSDK.SpeechConfig.fromAuthorizationToken(data.token, data.region);
        speechConfig.speechRecognitionLanguage = 'ko-KR';
        const audioConfig = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
        recognizer = new SpeechSDK.SpeechRecognizer(speechConfig, audioConfig);
        sttBtn.disabled = false;
    } catch (error) {
        console.error("음성 인식 초기화 실패:", error);
        sttBtn.innerHTML = '⚠️';
        sttBtn.title = "음성 인식 초기화 실패";
    }
  }

  initSpeech();

  on(sttBtn, 'click', () => {
      if (!recognizer) return;
      sttBtn.disabled = true;
      sttBtn.innerHTML = '👂';
      captionInput.value = '';
      autoGrow(captionInput)
      captionInput.placeholder = '말씀해주세요';
      recognizer.recognizeOnceAsync(result => {
          if (result.reason === SpeechSDK.ResultReason.RecognizedSpeech) {
              captionInput.value = result.text.replace(/[.]$/, '');
              captionInput.placeholder = '장면 설명을 입력하세요';
          } else {
              captionInput.placeholder = '음성 인식 실패. 다시 시도하세요.';
          }
          sttBtn.disabled = false;
          sttBtn.innerHTML = '🎤';
      });
  });
});