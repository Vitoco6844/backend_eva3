let tokens;
let refreshing;

function message(value) {
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) return value.map(message).join(' ');
  if (value && typeof value === 'object') {
    if (value.message) return message(value.message);
    if (value.detail) return message(value.detail);
    return Object.entries(value).map(([key, item]) => key + ': ' + message(item)).join(' ');
  }
  return '';
}

async function request(path, method, data, access) {
  const headers = { Accept: 'application/json' };
  if (access) headers.Authorization = 'Bearer ' + access;
  if (data !== undefined) headers['Content-Type'] = 'application/json';
  const response = await fetch('/api/' + path, {
    method, headers, body: data === undefined ? undefined : JSON.stringify(data),
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(message(body) || 'Error HTTP ' + response.status);
    error.status = response.status;
    throw error;
  }
  return body;
}

export function logout() { tokens = undefined; }

export async function login(credentials) {
  tokens = await request('auth/token/', 'POST', credentials);
  return api('auth/me/');
}

export async function api(path, method = 'GET', data) {
  const session = tokens;
  try {
    return await request(path, method, data, session?.access);
  } catch (error) {
    if (error.status !== 401 || !session || session !== tokens) throw error;
    if (!refreshing) {
      refreshing = request('auth/refresh/', 'POST', { refresh: session.refresh })
        .then(({access}) => { if (tokens === session) session.access = access; })
        .catch((failure) => {
          if (tokens === session) {
            logout();
            window.dispatchEvent(new Event('buildcorp-expired'));
          }
          throw failure;
        })
        .finally(() => { refreshing = undefined; });
    }
    await refreshing;
    if (tokens !== session) throw error;
    return request(path, method, data, session.access);
  }
}

export async function all(path) {
  const rows = [];
  let page = 1;
  while (true) {
    const data = await api(path + (path.includes('?') ? '&' : '?') + 'page=' + page);
    rows.push(...data.results);
    if (!data.next) return rows;
    page += 1;
  }
}
