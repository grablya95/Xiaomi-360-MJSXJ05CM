const $ = id => document.getElementById(id);
let currentPath = '/mnt/sdcard';

function api(action, params = {}) {
  const query = new URLSearchParams({action, ...params});
  return `/cgi-bin/files.cgi?${query.toString()}`;
}

function setMessage(text, bad = false) {
  const el = $('message');
  el.textContent = text;
  el.className = bad ? 'bad' : 'muted';
}

function humanSize(bytes) {
  bytes = Number(bytes) || 0;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function humanTime(epoch) {
  epoch = Number(epoch) || 0;
  if (!epoch) return '—';
  return new Date(epoch * 1000).toLocaleString();
}

function joinPath(dir, name) {
  return `${dir.replace(/\/+$/, '')}/${name}`;
}

async function load(path = currentPath) {
  setMessage('Читаю папку…');
  const data = await fetch(api('list', {path}), {cache: 'no-store'}).then(r => r.json());
  if (!data.ok) {
    setMessage(data.error || 'Ошибка чтения', true);
    return;
  }
  currentPath = data.path;
  $('pathBox').value = currentPath;
  $('currentPath').textContent = currentPath;
  renderRows(data);
  setMessage(`Найдено: ${data.items.length}`);
}

function renderRows(data) {
  const rows = [];
  if (data.parent) {
    rows.push(`<tr>
      <td><a href="#" data-open="${data.parent}">..</a></td>
      <td class="hide-sm">dir</td>
      <td class="hide-sm">—</td>
      <td class="hide-sm">—</td>
      <td class="actions-cell"></td>
    </tr>`);
  }
  for (const item of data.items) {
    const full = joinPath(data.path, item.name);
    const icon = item.type === 'dir' ? '📁' : item.type === 'link' ? '🔗' : '📄';
    const name = item.type === 'dir'
      ? `<a href="#" data-open="${encodeHtml(full)}">${icon} ${encodeHtml(item.name)}</a>`
      : `${icon} ${encodeHtml(item.name)}`;
    const download = item.type === 'file'
      ? `<a class="primary small" href="${api('download', {path: full})}">Скачать</a>`
      : '';
    rows.push(`<tr>
      <td>${name}</td>
      <td class="hide-sm">${encodeHtml(item.type)}</td>
      <td class="hide-sm">${item.type === 'file' ? humanSize(item.size) : '—'}</td>
      <td class="hide-sm">${humanTime(item.mtime)}</td>
      <td class="actions-cell">
        ${download}
        <button class="ghost small" data-rename="${encodeHtml(full)}">Переим.</button>
        <button class="danger small" data-delete="${encodeHtml(full)}">Удалить</button>
      </td>
    </tr>`);
  }
  $('fileRows').innerHTML = rows.join('') || '<tr><td colspan="5" class="muted">Папка пустая.</td></tr>';
}

function encodeHtml(text) {
  return String(text).replace(/[&<>"']/g, ch => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[ch]));
}

document.addEventListener('click', async event => {
  const open = event.target.closest('[data-open]');
  if (open) {
    event.preventDefault();
    await load(open.dataset.open);
    return;
  }
  const del = event.target.closest('[data-delete]');
  if (del) {
    const path = del.dataset.delete;
    if (!confirm(`Удалить?\n${path}`)) return;
    const data = await fetch(api('delete', {path}), {method: 'POST'}).then(r => r.json());
    setMessage(data.ok ? 'Удалено.' : data.error, !data.ok);
    await load();
    return;
  }
  const ren = event.target.closest('[data-rename]');
  if (ren) {
    const path = ren.dataset.rename;
    const oldName = path.split('/').pop();
    const name = prompt('Новое имя:', oldName);
    if (!name || name === oldName) return;
    const data = await fetch(api('rename', {path, name}), {method: 'POST'}).then(r => r.json());
    setMessage(data.ok ? 'Переименовано.' : data.error, !data.ok);
    await load();
  }
});

$('goPath').addEventListener('click', () => load($('pathBox').value.trim() || '/mnt/sdcard'));
$('refreshButton').addEventListener('click', () => load());
$('rootSd').addEventListener('click', () => load('/mnt/sdcard'));
$('rootData').addEventListener('click', () => load('/mnt/data'));
$('rootTmp').addEventListener('click', () => load('/tmp'));

$('mkdirButton').addEventListener('click', async () => {
  const name = prompt('Имя папки:');
  if (!name) return;
  const data = await fetch(api('mkdir', {path: currentPath, name}), {method: 'POST'}).then(r => r.json());
  setMessage(data.ok ? 'Папка создана.' : data.error, !data.ok);
  await load();
});

$('uploadButton').addEventListener('click', async () => {
  const file = $('uploadFile').files[0];
  if (!file) {
    setMessage('Сначала выбери файл.', true);
    return;
  }
  setMessage(`Загружаю ${file.name}…`);
  const data = await fetch(api('upload', {path: currentPath, name: file.name}), {
    method: 'POST',
    body: file
  }).then(r => r.json());
  setMessage(data.ok ? `Загружено ${humanSize(data.bytes)}.` : data.error, !data.ok);
  await load();
});

load().catch(error => setMessage(error.message, true));
