import { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { api, login, logout } from './api';
import { Fields, Signature, check, field, optional, ref, roles, values } from './fields';
import '../../static/css/app.css';
import './style.css';

const name = field('name', 'Nombre');
const active = check('active', 'Activo', true);
const note = optional('notes', 'Observaciones', 'textarea');
const role = field('role', 'Rol', 'select', {options: roles});
const roleLabel = value => Object.fromEntries(roles)[value] ?? 'Contratista';
const date = value => value ? new Date(value).toLocaleString('es-CL') : '—';

const catalog = {
  assets: { title: 'Herramientas', label: r => r.code + ' · ' + r.name, fields: [
    field('code', 'Código'), name, optional('serial', 'Número de serie'),
    ref('category', 'Categoría', 'categories/'), ref('warehouse', 'Bodega', 'warehouses/'),
    optional('description', 'Descripción', 'textarea'), field('daily_rate', 'Tarifa de referencia (CLP)', 'number'),
  ] },
  sites: { title: 'Obras', fields: [name, field('address', 'Dirección'), active] },
  warehouses: { title: 'Bodegas', fields: [name, ref('site', 'Obra', 'sites/'), active] },
  categories: { title: 'Categorías', fields: [name, active] },
  contractors: { title: 'Contratistas', fields: [
    name, field('tax_id', 'RUT / identificador'), optional('email', 'Correo', 'email'),
    optional('phone', 'Teléfono'), active, check('manual_block', 'Bloqueo manual'),
  ] },
  'maintenance-plans': { title: 'Planes de mantenimiento', label: r => 'Herramienta #' + r.asset, fields: [
    ref('asset', 'Herramienta', 'assets/'), optional('due_at', 'Próxima revisión', 'datetime-local'),
    field('due_hours', 'Umbral de horas', 'number', {optional: true, step: '0.01'}),
  ] },
};

function Form({fields, initial, submit, close, signature, children, label = 'Guardar'}) {
  const canvas = useRef();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function save(event) {
    event.preventDefault();
    if (busy) return;
    if (fields.some(f => f.source && !event.currentTarget.elements.namedItem(f.name))) return;
    const data = values(fields, event.currentTarget);
    if (signature) data.signature = canvas.current.toDataURL('image/png');
    setBusy(true);
    setError('');
    try { await submit(data); }
    catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }
  return <form className="panel form-panel" onSubmit={save}>
    <Fields fields={fields} initial={initial}/>
    {children}
    {signature && <Signature canvas={canvas}/>}
    {error && <p className="message error" role="alert">{error}</p>}
    <div className="actions"><button className="button" disabled={busy}>{busy ? 'Guardando…' : label}</button>
      {close && <button type="button" className="button secondary" onClick={close}>Cancelar</button>}
    </div>
  </form>;
}

function useRows(endpoint) {
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState('');
  const [version, setVersion] = useState(0);
  const [state, setState] = useState({});
  useEffect(() => {
    let alive = true;
    setState({loading: true});
    api(endpoint + '?page=' + page + '&q=' + encodeURIComponent(query))
      .then(data => { if (alive) setState({data}); })
      .catch(error => { if (alive) setState({error: error.message}); });
    return () => { alive = false; };
  }, [endpoint, page, query, version]);
  return {...state, page, setPage, search: q => { setPage(1); setQuery(q); },
    reload: () => { setPage(1); setVersion(v => v + 1); }};
}

function Rows({state, columns}) {
  if (state.error) return <p className="message error" role="alert">{state.error}</p>;
  if (state.loading || !state.data) return <p>Cargando…</p>;
  const {results, previous, next} = state.data;
  if (!results.length) return <p className="panel">No hay registros.</p>;
  return <><div className="panel table-wrap"><table><thead><tr>{columns.map(([heading]) =>
    <th key={heading} scope="col">{heading}</th>)}</tr></thead><tbody>{results.map(row =>
    <tr key={row.id}>{columns.map(([heading, render]) => <td key={heading}>{render(row)}</td>)}</tr>)}</tbody></table></div>
    {(previous || next) && <nav className="actions" aria-label="Paginación">
      <button className="button secondary" disabled={!previous} onClick={() => state.setPage(state.page - 1)}>Anterior</button>
      <span>Página {state.page}</span>
      <button className="button secondary" disabled={!next} onClick={() => state.setPage(state.page + 1)}>Siguiente</button>
    </nav>}</>;
}

function Search({state}) {
  return <form className="filters" onSubmit={e => { e.preventDefault(); state.search(new FormData(e.currentTarget).get('q')); }}>
    <input name="q" aria-label="Buscar" placeholder="Buscar" maxLength="150"/><button className="button secondary">Buscar</button>
  </form>;
}

function Workspace({section, user}) {
  const admin = user.is_superuser || user.role === 'ADMIN';
  const state = useRows(section + '/');
  const [editor, setEditor] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const close = () => setEditor(null);
  const open = (title, fields, submit, extra) => {
    setSuccess('');
    setError('');
    setEditor({title, fields, submit, ...extra});
  };
  async function write(path, method, data) {
    await api(path, method, data);
    close();
    state.reload();
    setSuccess('Cambios guardados.');
  }
  async function remove(row) {
    if (!window.confirm('¿Eliminar el registro #' + row.id + '?')) return;
    setError('');
    try { await write(section + '/' + row.id + '/', 'DELETE'); }
    catch (failure) { setError(failure.message); }
  }
  const detail = row => section + '/' + row.id + '/';
  const action = (row, verb, title, fields, extra = {}) => open(title, fields, async data => {
    if (verb === 'approve') data.quote = (await api(detail(row) + 'approval-quote/')).quote;
    return write(detail(row) + verb + '/', 'POST', data);
  }, extra);
  const config = catalog[section];
  let title, columns, create, search;
  if (config) {
    title = config.title;
    const editable = section !== 'contractors' || admin;
    search = section === 'assets';
    if (editable) create = () => open('Crear registro', config.fields, data => write(section + '/', 'POST', data));
    columns = [
      ['Registro', r => config.label ? config.label(r) : r.name],
      ['Estado o referencia', r => r.status ?? (r.active !== undefined ? (r.active ? 'Activo' : 'Inactivo') :
        [date(r.due_at), r.due_hours && r.due_hours + ' h'].filter(Boolean).join(' · '))],
      ['Acciones', r => editable && <div className="actions">
        <button className="button secondary" onClick={() => {
          const fields = config.fields.filter(f => !(section === 'assets' && f.name === 'warehouse') &&
            !(section === 'maintenance-plans' && f.name === 'asset'));
          const initial = {...r};
          if (r.due_at) {
            const time = new Date(r.due_at);
            initial.due_at = new Date(time.getTime() - time.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
          }
          open('Editar registro', fields, data => write(detail(r), 'PATCH', data), {initial});
        }}>Editar</button>
        {section === 'assets' ? <>
          <button className="button secondary" onClick={() => action(r, 'transfer', 'Trasladar herramienta',
            [ref('warehouse_id', 'Nueva bodega', 'warehouses/'), field('reason', 'Motivo')])}>Trasladar</button>
          <button className="button secondary" onClick={() => action(r, 'retire', 'Dar de baja',
            [field('reason', 'Motivo')])}>Dar de baja</button>
        </> : admin && section !== 'maintenance-plans' && <button className="button secondary" onClick={() => remove(r)}>Eliminar</button>}
      </div>],
    ];
  } else if (section === 'users') {
    title = 'Usuarios';
    search = true;
    create = () => open('Crear cuenta de personal', [
      field('username', 'Usuario'), optional('first_name', 'Nombre'), optional('last_name', 'Apellido'),
      optional('email', 'Correo', 'email'), role, field('password1', 'Contraseña', 'password'),
      field('password2', 'Confirmar contraseña', 'password'),
    ], data => write('users/', 'POST', data));
    columns = [['Usuario', r => r.username], ['Correo', r => r.email], ['Rol', r => roleLabel(r.role)],
      ['Estado', r => r.is_active ? 'Activa' : 'Inactiva'],
      ['Acciones', r => r.id === user.id || r.is_superuser ? 'Protegida' :
        <button className="button secondary" onClick={() => open('Editar ' + r.username, [
          ...(r.role === 'CONTRATISTA' ? [] : [role]), check('is_active', 'Cuenta activa'),
        ], data => write(detail(r), 'PATCH', data), {initial: r})}>Editar</button>]];
  } else if (section === 'rental-requests') {
    title = 'Solicitudes';
    create = () => {
      const key = crypto.randomUUID();
      open('Nueva solicitud interna', [
        ref('contractor_id', 'Contratista', 'contractors/'), field('site_name', 'Obra solicitada'),
        field('site_address', 'Dirección de la obra'), field('responsible', 'Responsable'),
        field('starts_at', 'Inicio previsto', 'datetime-local'), field('ends_at', 'Devolución prevista', 'datetime-local'),
        ref('asset_ids', 'Herramientas (puedes seleccionar varias)', 'assets/?status=DISPONIBLE', 'multiple'), note,
      ], data => write(section + '/', 'POST', {...data, submit_key: key}));
    };
    columns = [['Solicitud', r => '#' + r.id + ' · ' + r.contractor_name],
      ['Herramientas', r => r.items.map(i => i.asset_name).join(', ')],
      ['Período', r => date(r.starts_at) + ' → ' + date(r.ends_at)],
      ['Estado', r => r.status + (r.internal ? ' · Interna' : ' · EVA 3')],
      ['Acciones', r => <div className="actions">
        {r.internal && r.status === 'PENDIENTE' &&
          <button className="button" onClick={() => action(r, 'approve', 'Aprobar y reservar', [ref('site_id', 'Obra', 'sites/')])}>Aprobar</button>}
        {(r.internal && r.status === 'APROBADA' || r.status === 'PAGADA') &&
          <button className="button" onClick={() => action(r, 'fulfill', 'Registrar entrega', [field('responsible', 'Responsable')],
            {signature: true, initial: r})}>Entregar</button>}
        {['PENDIENTE', 'APROBADA'].includes(r.status) &&
          <button className="button secondary" onClick={() => action(r, 'reject', 'Rechazar solicitud',
            [field('reason', 'Motivo', 'textarea')])}>Rechazar</button>}
      </div>]];
  } else if (section === 'loans') {
    title = 'Préstamos';
    columns = [['Préstamo', r => '#' + r.id + ' · ' + r.responsible],
      ['Vencimiento', r => date(r.due_at)],
      ['Estado', r => r.closed_at ? 'Cerrado' : 'En curso'],
      ['Herramientas', r => r.items.map(i => i.asset_name + (i.returned_at ? ' (devuelta)' : '')).join(', ')],
      ['Devolución', r => <div className="actions">{r.items.filter(i => !i.returned_at).map(i =>
        <button key={i.id} className="button secondary" onClick={() => open('Devolver ' + i.asset_name, [
          field('usage_hours', 'Horas de uso', 'number', {step: '0.01', initial: '0'}), check('damaged', 'Con daños'), note,
        ], ({signature, ...data}) => write(detail(r) + 'return/', 'POST', {
          signature, items: [{...data, item_id: i.id}],
        }), {signature: true})}>Devolver {i.asset_name}</button>)}</div>]];
  } else if (section === 'maintenance-jobs') {
    title = 'Trabajos de mantenimiento';
    create = () => open('Iniciar mantenimiento', [ref('asset_id', 'Herramienta', 'assets/'),
      field('notes', 'Observaciones', 'textarea')], data => write(section + '/', 'POST', data));
    columns = [['Trabajo', r => '#' + r.id + ' · Herramienta #' + r.asset], ['Inicio', r => date(r.started_at)],
      ['Término', r => date(r.finished_at)], ['Acciones', r => !r.finished_at &&
        <button className="button secondary" onClick={() => action(r, 'finish', 'Cerrar mantenimiento', [
          field('notes', 'Observaciones', 'textarea'), optional('next_due_at', 'Próxima revisión', 'datetime-local'),
          field('next_due_hours', 'Próximo umbral de horas', 'number', {optional: true, step: '0.01'}),
        ])}>Finalizar</button>]];
  } else {
    title = 'Cobros históricos';
    columns = [['Cargo', r => '#' + r.id + ' · ' + r.kind], ['Préstamo', r => r.loan ?? '—'],
      ['Monto', r => '$' + Number(r.amount).toLocaleString('es-CL')],
      ['Estado', r => r.voided_at ? 'Anulado' : r.paid_at ? 'Pagado' : 'Pendiente']];
  }
  return <><header className="page-heading"><h1>{title}</h1>{create && <button className="button" onClick={create}>Crear</button>}</header>
    {search && <Search state={state}/>}
    {error && <p className="message error" role="alert">{error}</p>}
    {success && <p className="message" role="status">{success}</p>}
    {editor && <section key={editor.title}><h2>{editor.title}</h2><Form {...editor} close={close}/></section>}
    <Rows state={state} columns={columns}/>
  </>;
}

function Alerts() {
  const [data, setData] = useState();
  const [error, setError] = useState('');
  useEffect(() => { api('alerts/').then(setData).catch(e => setError(e.message)); }, []);
  return <><div className="page-heading"><h1>Alertas y bloqueos</h1></div>{error && <p role="alert">{error}</p>}
    {data && <div className="cards"><section className="panel"><h2>Préstamos vencidos</h2>
      {data.overdue.length ? <ul>{data.overdue.map(r => <li key={r.id}>#{r.id} · {r.contractor__name} · {date(r.due_at)}</li>)}</ul> : <p>Ninguno.</p>}
    </section><section className="panel"><h2>Contratistas bloqueados</h2>
      {data.blocked.length ? <ul>{data.blocked.map(r => <li key={r.id}>{r.name}</li>)}</ul> : <p>Ninguno.</p>}
    </section></div>}</>;
}

function Overview({navigate}) {
  const [data, setData] = useState();
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    api('overview/').then(result => { if (active) setData(result); })
      .catch(failure => { if (active) setError(failure.message); });
    return () => { active = false; };
  }, []);

  const metrics = [
    ['available', 'Herramientas disponibles', 'assets'],
    ['open_count', 'Préstamos en curso', 'loans'],
    ['overdue_count', 'Devoluciones vencidas', 'alerts'],
    ['pending_count', 'Cargos pendientes', 'charges'],
  ];
  return <>
    <header className="page-heading">
      <div><p className="subtitle">Estado de las operaciones</p><h1>Todo listo para<br/>la próxima entrega.</h1></div>
      <button className="button" onClick={() => navigate('rental-requests')}>Gestionar solicitudes</button>
    </header>
    {error && <p className="message error" role="alert">{error}</p>}
    <div className="metrics">
      {metrics.map(([key, label, page]) => <button key={key} onClick={() => navigate(page)}>
        <strong>{data?.[key] ?? '—'}</strong><span>{label}</span>
      </button>)}
    </div>
    <section className="panel table-wrap">
      <div className="section-heading"><h2>En terreno</h2>
        <button className="link-button" onClick={() => navigate('loans')}>Ver préstamos</button>
      </div>
      {data?.loans.length ? <table>
        <thead><tr><th scope="col">Préstamo</th><th scope="col">Contratista</th><th scope="col">Obra</th><th scope="col">Vencimiento</th></tr></thead>
        <tbody>{data.loans.map(row => <tr key={row.id}>
          <td>#{row.id}</td><td>{row.contractor__name}</td><td>{row.site__name}</td><td>{date(row.due_at)}</td>
        </tr>)}</tbody>
      </table> : <p className="empty">{data ? 'No hay préstamos en curso.' : error ? 'Resumen no disponible.' : 'Cargando préstamos…'}</p>}
    </section>
    <section className="maintenance-callout">
      <div><h2>Mantenimiento preventivo</h2><p>Consulta las fechas y horas de uso previstas para cada herramienta.</p></div>
      <button className="button secondary" onClick={() => navigate('maintenance-plans')}>Revisar mantenimiento</button>
    </section>
  </>;
}

const navigation = [
  [
    ['overview', 'Resumen'], ['rental-requests', 'Solicitudes recibidas'], ['assets', 'Herramientas'],
    ['loans', 'Préstamos'], ['maintenance-plans', 'Planes de mantenimiento'],
    ['maintenance-jobs', 'Trabajos de mantenimiento'], ['alerts', 'Alertas y bloqueos'],
    ['charges', 'Cobros históricos'],
  ],
  [
    ['contractors', 'Contratistas'], ['sites', 'Obras'], ['warehouses', 'Bodegas'],
    ['categories', 'Categorías'], ['users', 'Administración'],
  ],
];

function Brand({onClick}) {
  const content = <><span className="brandmark" aria-hidden="true">B<span>+</span></span>
    <span>BuildCorp<small>Control de herramientas</small></span></>;
  return onClick ? <button type="button" className="brand" onClick={onClick}>{content}</button> :
    <div className="brand">{content}</div>;
}

function App() {
  const [user, setUser] = useState();
  const [section, setSection] = useState('overview');
  useEffect(() => {
    const expire = () => setUser(undefined);
    window.addEventListener('buildcorp-expired', expire);
    return () => window.removeEventListener('buildcorp-expired', expire);
  }, []);
  if (!user) return <>
    <aside className="sidebar"><Brand/><div className="sidebar-foot">BuildCorp / EVA 4</div></aside>
    <main className="login">
      <section className="login-intro">
        <div><p className="subtitle">Administración de BuildCorp</p><h1>Todo listo para<br/>seguir construyendo.</h1></div>
        <img className="brand-icon" src={import.meta.env.VITE_BRAND_URL || '/buildcorp.png'} alt=""/>
      </section>
      <Form fields={[field('username', 'Usuario'), field('password', 'Contraseña', 'password', {autocomplete: 'current-password'})]}
        label="Ingresar" submit={async data => { setSection('overview'); setUser(await login(data)); }}/>
    </main>
  </>;
  const admin = user.is_superuser || user.role === 'ADMIN';
  const today = new Intl.DateTimeFormat('es-CL', {day: 'numeric', month: 'short', year: 'numeric'}).format(new Date());
  return <>
    <a className="skip" href="#content">Saltar al contenido</a>
    <aside className="sidebar">
      <Brand onClick={() => setSection('overview')}/>
      <nav aria-label="Operaciones">
        {navigation.map((group, index) => <div className="nav-group" key={index}>
          {group.filter(([key]) => key !== 'users' || admin).map(([key, label]) =>
            <button key={key} aria-current={section === key ? 'page' : undefined} onClick={() => setSection(key)}>{label}</button>)}
        </div>)}
      </nav>
      <div className="account"><strong>{user.username}</strong><small>{roleLabel(user.role)}</small>
        <button className="text-button" onClick={() => { logout(); setUser(undefined); }}>Cerrar sesión</button>
      </div>
      <div className="sidebar-foot">BuildCorp / EVA 4<br/>Gestión de activos de construcción</div>
    </aside>
    <main id="content">
      <div className="topbar"><span>Operaciones / {today}</span><span className="environment">Proyecto académico</span></div>
      {section === 'overview' ? <Overview navigate={setSection}/> :
        section === 'alerts' ? <Alerts/> : <Workspace key={section} section={section} user={user}/>}
      <footer>BuildCorp · Trazabilidad de herramientas y mantenimiento preventivo</footer>
    </main>
  </>;
}

createRoot(document.getElementById('root')).render(<App/>);
