(() => {
  "use strict";
  const csrf = document.querySelector('meta[name="csrf-token"]').content;
  const form = document.getElementById('convert-form');
  const message = document.getElementById('convert-message');
  const previewSection = document.getElementById('preview-section');
  const preview = document.getElementById('markdown-preview');
  const previewTitle = document.getElementById('preview-title');
  const folderStatus = document.getElementById('folder-status');
  let result = null;
  let directoryHandle = null;

  function setMessage(text='', kind=''){message.textContent=text;message.className=`inline-message ${kind}`;}
  function openDb(){return new Promise((resolve,reject)=>{const request=indexedDB.open('seoblue-obsidian',1);request.onupgradeneeded=()=>request.result.createObjectStore('settings');request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);});}
  async function saveHandle(handle){const db=await openDb();await new Promise((resolve,reject)=>{const tx=db.transaction('settings','readwrite');tx.objectStore('settings').put(handle,'directory');tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error);});db.close();}
  async function loadHandle(){try{const db=await openDb();const handle=await new Promise((resolve,reject)=>{const req=db.transaction('settings').objectStore('settings').get('directory');req.onsuccess=()=>resolve(req.result||null);req.onerror=()=>reject(req.error);});db.close();return handle;}catch{return null;}}
  async function ensurePermission(handle){if(!handle)return false;const opts={mode:'readwrite'};if(await handle.queryPermission(opts)==='granted')return true;return await handle.requestPermission(opts)==='granted';}
  function updateFolderStatus(){folderStatus.textContent=directoryHandle?`선택됨: ${directoryHandle.name}`:'선택된 폴더 없음 · 일반 다운로드 사용';}
  async function chooseFolder(){if(!('showDirectoryPicker' in window)){setMessage('이 브라우저는 폴더 직접 저장을 지원하지 않아 일반 다운로드를 사용합니다.','error');return;}try{const handle=await window.showDirectoryPicker({mode:'readwrite',startIn:'downloads'});if(await ensurePermission(handle)){directoryHandle=handle;await saveHandle(handle);updateFolderStatus();setMessage('저장 폴더 권한을 기억했습니다.','success');}}catch(error){if(error.name!=='AbortError')setMessage('폴더 권한을 설정하지 못했습니다.','error');}}
  async function uniqueFileHandle(directory, filename){const dot=filename.toLowerCase().endsWith('.md')?filename.slice(0,-3):filename;for(let i=0;i<1000;i++){const candidate=i?`${dot} (${i}).md`:`${dot}.md`;try{await directory.getFileHandle(candidate); }catch(error){if(error.name==='NotFoundError')return directory.getFileHandle(candidate,{create:true});throw error;}}throw new Error('사용 가능한 파일 이름을 만들지 못했습니다.');}
  function browserDownload(filename, markdown){const blob=new Blob([markdown],{type:'text/markdown;charset=utf-8'});const link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download=filename;document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(link.href),1000);}
  async function saveMarkdown(){if(!result)return;try{if(directoryHandle&&await ensurePermission(directoryHandle)){const file=await uniqueFileHandle(directoryHandle,result.filename);const writer=await file.createWritable();await writer.write(result.markdown);await writer.close();setMessage(`${file.name} 파일을 선택한 폴더에 저장했습니다.`,'success');}else{browserDownload(result.filename,result.markdown);setMessage('브라우저 일반 다운로드로 저장했습니다. 다운로드 기본 경로를 C:\\obsidian\\download로 설정하면 해당 폴더에 저장됩니다.','success');}}catch(error){setMessage(`저장하지 못했습니다: ${error.message}`,'error');}}
  form.addEventListener('submit',async event=>{event.preventDefault();const button=document.getElementById('convert-button');button.disabled=true;button.textContent='가져오는 중…';setMessage();previewSection.hidden=true;try{const response=await fetch('/api/obsidian/convert',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,Accept:'application/json'},body:JSON.stringify({url:document.getElementById('share-url').value})});const data=await response.json().catch(()=>({error:'서버 응답을 해석할 수 없습니다.'}));if(!response.ok)throw new Error(data.error||'변환하지 못했습니다.');result=data;preview.textContent=data.markdown;previewTitle.textContent=data.title;previewSection.hidden=false;setMessage(`${data.messageCount}개 메시지를 변환했습니다.`,'success');preview.focus();}catch(error){setMessage(error.message,'error');}finally{button.disabled=false;button.textContent='가져와서 변환';}});
  document.getElementById('choose-folder').addEventListener('click',chooseFolder);
  document.getElementById('save-markdown').addEventListener('click',saveMarkdown);
  (async()=>{directoryHandle=await loadHandle();if(directoryHandle&&await directoryHandle.queryPermission({mode:'readwrite'})!=='granted')directoryHandle=null;updateFolderStatus();})();
})();
