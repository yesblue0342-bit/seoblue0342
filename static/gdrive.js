(() => {
  "use strict";
  const csrf = document.querySelector('meta[name="csrf-token"]').content;
  const listEl = document.getElementById("file-list");
  const messageEl = document.getElementById("drive-message");
  const breadcrumbEl = document.getElementById("breadcrumb");
  const dropZoneEl = document.getElementById("drive-drop-zone");
  const capabilityEl = document.getElementById("drive-capability");
  const state = { folderId: "root", crumbs: [{ id: "root", name: "내 폴더" }], files: [], writes: false };

  const escapeHtml = value => String(value ?? "").replace(/[&<>'"]/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[ch]);
  const formatSize = value => { const n=Number(value); if(!Number.isFinite(n)||n<=0)return "—"; const u=["B","KB","MB","GB"]; let i=0,v=n; while(v>=1024&&i<u.length-1){v/=1024;i++;} return `${v.toFixed(i?1:0)} ${u[i]}`; };
  const formatDate = value => value ? new Intl.DateTimeFormat("ko-KR", {dateStyle:"medium",timeStyle:"short"}).format(new Date(value)) : "—";
  const typeName = mime => ({
    "application/vnd.google-apps.folder":"폴더",
    "application/vnd.google-apps.document":"문서",
    "application/vnd.google-apps.spreadsheet":"스프레드시트",
    "application/vnd.google-apps.presentation":"프레젠테이션",
    "application/vnd.google-apps.drawing":"그림"
  })[mime] || (mime ? mime.split('/').at(-1).replace(/^vnd\./,'') : "파일");
  function setMessage(text="", kind="") { messageEl.textContent=text; messageEl.className=`inline-message ${kind}`; }
  async function api(url, options={}) {
    const headers = {Accept:"application/json", ...(options.headers||{})};
    if (!['GET','HEAD'].includes((options.method||'GET').toUpperCase())) headers['X-CSRF-Token']=csrf;
    const response = await fetch(url, {...options, headers});
    const data = await response.json().catch(() => ({error:"서버 응답을 해석할 수 없습니다."}));
    if(!response.ok) throw new Error(data.error||data.message||"요청에 실패했습니다.");
    return data;
  }
  function renderBreadcrumb(){
    breadcrumbEl.innerHTML=state.crumbs.map((c,i)=>`<button type="button" data-crumb="${i}" data-drop-folder="${escapeHtml(c.id)}">${escapeHtml(c.name)}</button>${i<state.crumbs.length-1?'<span>/</span>':''}`).join('');
    breadcrumbEl.querySelectorAll('[data-crumb]').forEach(btn=>{
      const i=Number(btn.dataset.crumb);
      btn.addEventListener('click',()=>{state.crumbs=state.crumbs.slice(0,i+1);loadFolder(state.crumbs[i].id);});
      bindFolderDropTarget(btn,()=>btn.dataset.dropFolder);
    });
  }
  function renderFiles(){
    if(!state.files.length){listEl.innerHTML='<div class="empty-state">표시할 파일이나 폴더가 없습니다.</div>';return;}
    listEl.innerHTML=state.files.map(f=>`<article class="file-row" data-id="${escapeHtml(f.id)}">
      <span class="file-name"><span class="file-icon ${f.isFolder?'folder':'file'}" aria-hidden="true"></span><button type="button" data-open>${escapeHtml(f.name)}</button></span>
      <span data-label="유형">${escapeHtml(typeName(f.mimeType))}</span><span data-label="수정일">${escapeHtml(formatDate(f.modifiedTime))}</span><span data-label="크기">${escapeHtml(formatSize(f.size))}</span>
      <span class="file-actions">${f.isFolder?'<button type="button" data-open>열기</button>':`<a href="/api/g-drive/download/${encodeURIComponent(f.id)}">다운로드</a>`}${state.writes?`<button type="button" data-rename>이름 변경</button><button type="button" data-move>이동</button><button type="button" data-delete class="danger">삭제</button>`:''}</span></article>`).join('');
    listEl.querySelectorAll('.file-row').forEach(row=>{
      const file=state.files.find(f=>f.id===row.dataset.id);
      row.querySelectorAll('[data-open]').forEach(b=>b.addEventListener('click',()=>file.isFolder?openFolder(file):location.assign(`/api/g-drive/download/${encodeURIComponent(file.id)}`)));
      row.querySelector('[data-rename]')?.addEventListener('click',()=>renameFile(file));
      row.querySelector('[data-move]')?.addEventListener('click',()=>moveFile(file));
      row.querySelector('[data-delete]')?.addEventListener('click',()=>deleteFile(file));
      if(file.isFolder)bindFolderDropTarget(row,()=>file.id);
    });
  }
  async function loadFolder(id="root", search=""){
    state.folderId=id||"root"; listEl.innerHTML='<div class="empty-state">불러오는 중…</div>'; setMessage();
    try{const q=new URLSearchParams({folder_id:state.folderId});if(search)q.set('q',search);const d=await api(`/api/g-drive/files?${q}`);state.files=d.files||[];renderFiles();renderBreadcrumb();}
    catch(e){state.files=[];listEl.innerHTML='<div class="empty-state">파일 목록을 불러오지 못했습니다.</div>';setMessage(e.message,'error');}
  }
  function openFolder(file){state.crumbs.push({id:file.id,name:file.name});loadFolder(file.id);}
  async function mutate(action, body){setMessage('처리 중…');try{await api(`/api/g-drive/${action}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});setMessage('완료되었습니다.','success');await loadFolder(state.folderId);}catch(e){setMessage(e.message,'error');}}
  function renameFile(file){const name=prompt('새 이름을 입력하세요.',file.name);if(name&&name.trim()&&name.trim()!==file.name)mutate('rename',{file_id:file.id,name:name.trim()});}
  function moveFile(file){const target=prompt('이동할 폴더 ID를 입력하세요.');if(target&&target.trim())mutate('move',{file_id:file.id,target_parent_id:target.trim()});}
  function deleteFile(file){if(confirm(`“${file.name}”을(를) 휴지통으로 이동할까요?`))mutate('delete',{file_id:file.id,confirm:true});}
  function isFileDrag(event){
    const types=Array.from(event.dataTransfer?.types||[]);
    return types.includes('Files')||types.includes('application/x-moz-file')||(!types.length&&Boolean(event.dataTransfer));
  }
  function bindFolderDropTarget(element,getFolderId){
    element.classList.add('folder-drop-target');
    for(const type of ['dragenter','dragover'])element.addEventListener(type,event=>{
      if(!isFileDrag(event))return;
      event.preventDefault();event.stopPropagation();
      if(state.writes){event.dataTransfer.dropEffect='copy';element.classList.add('is-dragover');}
    });
    element.addEventListener('dragleave',event=>{if(!element.contains(event.relatedTarget))element.classList.remove('is-dragover');});
    element.addEventListener('drop',event=>{
      const files=event.dataTransfer?.files;
      if(!files?.length)return;
      event.preventDefault();event.stopPropagation();element.classList.remove('is-dragover');
      if(!state.writes){setMessage('현재 파일 저장소는 읽기 전용입니다.','error');return;}
      const parentId=getFolderId();
      if(parentId)uploadFiles(files,parentId);
    });
  }
  async function uploadFiles(fileList,parentId){
    const files=Array.from(fileList||[]);if(!files.length)return;
    setMessage(files.length===1?'업로드 중…':`${files.length}개 파일 업로드 중…`);
    let completed=0,error=null;
    try{for(const file of files){const fd=new FormData();fd.append('parent_id',parentId);fd.append('file',file);await api('/api/g-drive/upload',{method:'POST',body:fd});completed++;}}
    catch(err){error=err;}
    if(completed&&parentId===state.folderId)await loadFolder(state.folderId);
    if(error){setMessage(completed?`${completed}개 파일 업로드 후 실패했습니다. ${error.message}`:error.message,'error');return;}
    setMessage(completed===1?'업로드했습니다.':`${completed}개 파일을 업로드했습니다.`,'success');
  }
  async function init(){
    try{const c=await api('/api/g-drive/capabilities');state.writes=Boolean(c.writesEnabled);capabilityEl.textContent=c.configured?(state.writes?'연결됨 · 읽기/쓰기':'연결됨 · 읽기 전용'):'연결 설정 필요';capabilityEl.classList.add(c.configured?'ok':'warn');document.querySelectorAll('[data-write-only]').forEach(el=>el.hidden=!state.writes);}
    catch(e){capabilityEl.textContent='연결 확인 실패';capabilityEl.classList.add('warn');setMessage(e.message,'error');}
    await loadFolder();
  }
  document.getElementById('go-root').addEventListener('click',()=>{state.crumbs=[{id:'root',name:'내 폴더'}];loadFolder('root');});
  document.getElementById('go-up').addEventListener('click',()=>{if(state.crumbs.length>1){state.crumbs.pop();loadFolder(state.crumbs.at(-1).id);}});
  document.getElementById('refresh-drive').addEventListener('click',()=>loadFolder(state.folderId));
  document.getElementById('search-button').addEventListener('click',()=>loadFolder('root',document.getElementById('drive-search').value.trim()));
  document.getElementById('drive-search').addEventListener('keydown',e=>{if(e.key==='Enter')document.getElementById('search-button').click();});
  document.getElementById('new-folder').addEventListener('click',()=>{const name=prompt('새 폴더 이름');if(name&&name.trim())mutate('folder',{parent_id:state.folderId,name:name.trim()});});
  document.getElementById('file-upload').addEventListener('change',async e=>{await uploadFiles(e.target.files,state.folderId);e.target.value='';});
  bindFolderDropTarget(breadcrumbEl,()=>state.folderId);
  bindFolderDropTarget(dropZoneEl,()=>state.folderId);
  init();
})();
