import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  App as AntApp,
  Button,
  Descriptions,
  Form,
  Image,
  Input,
  InputNumber,
  Layout,
  Menu,
  Modal,
  Progress,
  Select,
  Space,
  Table,
  Tag,
  Typography
} from 'antd';
import {
  CloudServerOutlined,
  DatabaseOutlined,
  EyeOutlined,
  LoginOutlined,
  PlayCircleOutlined,
  SearchOutlined,
  StopOutlined,
  TeamOutlined,
  UserSwitchOutlined
} from '@ant-design/icons';
import { Account, api, CrawlerTask, Creator, DataAsset, LoginSession } from './api';

const { Header, Sider, Content } = Layout;
const terminalLoginStates = new Set(['success', 'failed', 'expired', 'cancelled']);

type PageKey = 'dashboard' | 'assets' | 'tasks' | 'accounts' | 'creators';

function sizeText(value: number) {
  if (!value) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  let index = 0;
  let size = value;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function statusColor(status: string) {
  if (status === 'success' || status === 'active' || status === 'imported') return 'green';
  if (status === 'failed' || status === 'expired' || status.includes('failed')) return 'red';
  if (status === 'cancelled') return 'default';
  return 'blue';
}

export default function App() {
  const [page, setPage] = useState<PageKey>('dashboard');
  return (
    <AntApp>
      <Layout className="shell">
        <Sider width={224} breakpoint="lg" collapsedWidth={0} className="side">
          <div className="brand"><CloudServerOutlined /> 数据采集平台</div>
          <Menu
            theme="dark"
            mode="inline"
            selectedKeys={[page]}
            onClick={(item) => setPage(item.key as PageKey)}
            items={[
              { key: 'dashboard', icon: <DatabaseOutlined />, label: '总览' },
              { key: 'assets', icon: <DatabaseOutlined />, label: '数据资产' },
              { key: 'tasks', icon: <PlayCircleOutlined />, label: '采集任务' },
              { key: 'accounts', icon: <UserSwitchOutlined />, label: '账号登录' },
              { key: 'creators', icon: <TeamOutlined />, label: '达人查询' }
            ]}
          />
        </Sider>
        <Layout>
          <Header className="top">
            <Typography.Title level={4} className="title">{titleFor(page)}</Typography.Title>
          </Header>
          <Content className="content">
            {page === 'dashboard' && <Dashboard />}
            {page === 'assets' && <Assets />}
            {page === 'tasks' && <Tasks />}
            {page === 'accounts' && <Accounts />}
            {page === 'creators' && <Creators />}
          </Content>
        </Layout>
      </Layout>
    </AntApp>
  );
}

function titleFor(page: PageKey) {
  return ({ dashboard: '总览', assets: '数据资产', tasks: '采集任务', accounts: '账号登录', creators: '达人查询' } as const)[page];
}

function Dashboard() {
  const [data, setData] = useState<Record<string, any>>();
  useEffect(() => { api.get('/dashboard').then((res) => setData(res.data)); }, []);
  const platforms = Object.entries(data?.creators_by_platform || {});
  return (
    <div className="panel">
      <Descriptions column={{ xs: 1, sm: 2, lg: 4 }} bordered size="small">
        <Descriptions.Item label="资产">{data?.assets ?? '-'}</Descriptions.Item>
        <Descriptions.Item label="任务">{data?.tasks ?? '-'}</Descriptions.Item>
        <Descriptions.Item label="账号">{data?.accounts ?? '-'}</Descriptions.Item>
        <Descriptions.Item label="平台">{platforms.length}</Descriptions.Item>
      </Descriptions>
      <Table
        className="table"
        rowKey="platform"
        dataSource={platforms.map(([platform, count]) => ({ platform, count }))}
        columns={[{ title: '平台', dataIndex: 'platform' }, { title: '达人快照数', dataIndex: 'count' }]}
        pagination={false}
      />
    </div>
  );
}

function Assets() {
  const { message } = AntApp.useApp();
  const [rows, setRows] = useState<DataAsset[]>([]);
  const [busyId, setBusyId] = useState<number>();
  const load = () => api.get('/assets').then((res) => setRows(res.data));
  useEffect(() => { void load(); }, []);
  const discover = async () => {
    const res = await api.post('/assets/discover');
    message.success(`发现 ${res.data.count} 个资产`);
    load();
  };
  const ingest = async (id: number) => {
    setBusyId(id);
    try {
      const res = await api.post(`/ingest/${id}`);
      message.success(res.data.status === 'registered_only' ? '资产已登记' : `导入 ${res.data.imported_rows || 0} 行`);
      load();
    } finally {
      setBusyId(undefined);
    }
  };
  return (
    <div className="panel">
      <Space className="toolbar"><Button type="primary" icon={<SearchOutlined />} onClick={discover}>发现资产</Button></Space>
      <Table
        rowKey="id"
        dataSource={rows}
        scroll={{ x: 900 }}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 72 },
          { title: '平台', dataIndex: 'platform', width: 140 },
          { title: '类型', dataIndex: 'asset_type', width: 160 },
          { title: '文件', dataIndex: 'file_name' },
          { title: '大小', dataIndex: 'file_size', width: 120, render: sizeText },
          { title: '状态', dataIndex: 'import_status', width: 140, render: (v: string) => <Tag color={statusColor(v)}>{v}</Tag> },
          { title: '操作', width: 110, render: (_: unknown, row: DataAsset) => <Button size="small" loading={busyId === row.id} onClick={() => ingest(row.id)}>导入</Button> }
        ]}
      />
    </div>
  );
}

function Tasks() {
  const { message } = AntApp.useApp();
  const [rows, setRows] = useState<CrawlerTask[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState<CrawlerTask>();
  const [form] = Form.useForm();
  const load = () => api.get('/tasks').then((res) => setRows(res.data));
  useEffect(() => {
    load();
    api.get('/accounts').then((res) => setAccounts(res.data));
    const timer = window.setInterval(load, 3000);
    return () => window.clearInterval(timer);
  }, []);
  const submit = async () => {
    const values = await form.validateFields();
    await api.post('/tasks', {
      platform: 'xingtu',
      task_type: 'author_square',
      account_id: values.account_id,
      params: { max_pages: values.max_pages, page_size: values.page_size }
    });
    message.success('任务已进入队列');
    setOpen(false);
    form.resetFields();
    load();
  };
  const cancel = async (id: number) => {
    await api.post(`/tasks/${id}/cancel`);
    message.success('已请求取消任务');
    load();
  };
  return (
    <div className="panel">
      <Space className="toolbar"><Button type="primary" icon={<PlayCircleOutlined />} onClick={() => setOpen(true)}>新建任务</Button></Space>
      <Table
        rowKey="id"
        dataSource={rows}
        scroll={{ x: 1000 }}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 72 },
          { title: '平台', dataIndex: 'platform', width: 110 },
          { title: '类型', dataIndex: 'task_type', width: 150 },
          { title: '状态', dataIndex: 'status', width: 110, render: (v: string) => <Tag color={statusColor(v)}>{v}</Tag> },
          { title: '进度', width: 180, render: (_: unknown, row: CrawlerTask) => <Progress percent={row.progress_total ? Math.round(row.progress_current / row.progress_total * 100) : 0} size="small" /> },
          { title: '日志', dataIndex: 'log_tail', ellipsis: true },
          {
            title: '操作', width: 150, fixed: 'right', render: (_: unknown, row: CrawlerTask) => (
              <Space>
                <Button aria-label="查看任务" title="查看任务" size="small" icon={<EyeOutlined />} onClick={() => setDetail(row)} />
                {['pending', 'running'].includes(row.status) && <Button danger aria-label="取消任务" title="取消任务" size="small" icon={<StopOutlined />} onClick={() => cancel(row.id)} />}
              </Space>
            )
          }
        ]}
      />
      <Modal title="新建星图采集任务" open={open} onOk={submit} onCancel={() => setOpen(false)} destroyOnHidden>
        <Form form={form} layout="vertical" initialValues={{ max_pages: 1, page_size: 20 }}>
          <Form.Item name="account_id" label="采集账号" rules={[{ required: true, message: '请选择账号' }]}>
            <Select options={accounts.filter((item) => item.platform === 'xingtu').map((item) => ({ value: item.id, label: `${item.display_name} · ${item.status}` }))} />
          </Form.Item>
          <Form.Item name="max_pages" label="采集页数"><InputNumber min={1} className="wide" /></Form.Item>
          <Form.Item name="page_size" label="每页数量"><InputNumber min={1} max={100} className="wide" /></Form.Item>
        </Form>
      </Modal>
      <Modal title={`任务 ${detail?.id ?? ''}`} open={Boolean(detail)} footer={null} onCancel={() => setDetail(undefined)}>
        {detail && <Descriptions column={1} bordered size="small">
          <Descriptions.Item label="状态"><Tag color={statusColor(detail.status)}>{detail.status}</Tag></Descriptions.Item>
          <Descriptions.Item label="进度">{detail.progress_current} / {detail.progress_total}</Descriptions.Item>
          <Descriptions.Item label="日志"><pre className="log-block">{detail.log_tail || '-'}</pre></Descriptions.Item>
          <Descriptions.Item label="错误"><pre className="log-block error-text">{detail.error_message || '-'}</pre></Descriptions.Item>
        </Descriptions>}
      </Modal>
    </div>
  );
}

function Accounts() {
  const { message } = AntApp.useApp();
  const [rows, setRows] = useState<Account[]>([]);
  const [open, setOpen] = useState(false);
  const [loginSession, setLoginSession] = useState<LoginSession>();
  const [loginOpen, setLoginOpen] = useState(false);
  const [code, setCode] = useState('');
  const [imageVersion, setImageVersion] = useState(0);
  const [form] = Form.useForm();
  const loginType = Form.useWatch('login_type', form);
  const load = () => api.get('/accounts').then((res) => setRows(res.data));
  useEffect(() => { void load(); }, []);
  useEffect(() => {
    if (!loginOpen || !loginSession || terminalLoginStates.has(loginSession.status)) return;
    const poll = async () => {
      const res = await api.get(`/login-sessions/${loginSession.id}`);
      setLoginSession(res.data);
      setImageVersion(Date.now());
      if (terminalLoginStates.has(res.data.status)) load();
    };
    const timer = window.setInterval(poll, 2000);
    return () => window.clearInterval(timer);
  }, [loginOpen, loginSession?.id, loginSession?.status]);
  const submit = async () => {
    const values = await form.validateFields();
    await api.post('/accounts', values);
    message.success('账号已加密保存');
    setOpen(false);
    form.resetFields();
    load();
  };
  const login = async (account: Account) => {
    const res = await api.post(`/accounts/${account.id}/login`, { mode: account.login_type });
    setLoginSession(res.data);
    setCode('');
    setImageVersion(Date.now());
    setLoginOpen(true);
  };
  const submitCode = async () => {
    if (!loginSession || !code.trim()) return;
    const res = await api.post(`/login-sessions/${loginSession.id}/submit-code`, { code: code.trim() });
    setLoginSession(res.data);
    setCode('');
    message.success('验证码已提交');
  };
  const cancelLogin = async () => {
    if (!loginSession) return;
    const res = await api.post(`/login-sessions/${loginSession.id}/cancel`);
    setLoginSession(res.data);
    load();
  };
  const test = async (account: Account) => {
    const res = await api.post(`/accounts/${account.id}/test`);
    message.info(res.data.message);
    load();
  };
  return (
    <div className="panel">
      <Space className="toolbar"><Button type="primary" icon={<UserSwitchOutlined />} onClick={() => setOpen(true)}>新增账号</Button></Space>
      <Table
        rowKey="id"
        dataSource={rows}
        scroll={{ x: 850 }}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 72 },
          { title: '平台', dataIndex: 'platform', width: 130 },
          { title: '名称', dataIndex: 'display_name' },
          { title: '登录方式', dataIndex: 'login_type', width: 110 },
          { title: '账号', dataIndex: 'username_masked', width: 150, render: (v: string) => v || '-' },
          { title: '手机号', dataIndex: 'phone_masked', width: 150, render: (v: string) => v || '-' },
          { title: '状态', dataIndex: 'status', width: 130, render: (v: string) => <Tag color={statusColor(v)}>{v}</Tag> },
          { title: '操作', width: 160, fixed: 'right', render: (_: unknown, row: Account) => <Space><Button size="small" icon={<LoginOutlined />} onClick={() => login(row)}>登录</Button><Button size="small" onClick={() => test(row)}>测试</Button></Space> }
        ]}
      />
      <Modal title="新增账号" open={open} onOk={submit} onCancel={() => setOpen(false)} destroyOnHidden>
        <Form form={form} layout="vertical" initialValues={{ platform: 'xingtu', login_type: 'qr' }} preserve={false}>
          <Form.Item name="platform" label="平台" rules={[{ required: true }]}>
            <Select options={[{ value: 'xingtu', label: '星图' }, { value: 'magnetic_juxing', label: '磁力聚星' }, { value: 'ks_feigua', label: '飞瓜快手' }, { value: 'feigua', label: '飞瓜' }]} />
          </Form.Item>
          <Form.Item name="display_name" label="显示名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="login_type" label="登录方式" rules={[{ required: true }]}>
            <Select options={[{ value: 'qr', label: '扫码' }, { value: 'password', label: '账号密码' }, { value: 'sms', label: '短信验证码' }, { value: 'manual', label: '人工验证' }]} />
          </Form.Item>
          {loginType === 'password' && <Form.Item name="username" label="用户名" rules={[{ required: true }]}><Input autoComplete="username" /></Form.Item>}
          {loginType === 'sms' && <Form.Item name="phone" label="手机号" rules={[{ required: true }]}><Input autoComplete="tel" /></Form.Item>}
          {loginType === 'password' && <Form.Item name="password" label="密码" rules={[{ required: true }]}><Input.Password autoComplete="current-password" /></Form.Item>}
        </Form>
      </Modal>
      <Modal title="登录会话" open={loginOpen} footer={null} width={720} onCancel={() => setLoginOpen(false)} destroyOnHidden>
        {loginSession && <Space direction="vertical" size="middle" className="wide">
          <Alert
            type={loginSession.status === 'failed' ? 'error' : loginSession.status === 'success' ? 'success' : 'info'}
            message={<Space><Tag color={statusColor(loginSession.status)}>{loginSession.status}</Tag>{loginSession.prompt_message || loginSession.error_message}</Space>}
          />
          {!terminalLoginStates.has(loginSession.status) && <Image
            className="login-shot"
            preview={false}
            fallback="data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs="
            src={`/api/login-sessions/${loginSession.id}/screenshot?t=${imageVersion}`}
          />}
          {loginSession.mode === 'sms' && !terminalLoginStates.has(loginSession.status) && <Space.Compact className="wide">
            <Input value={code} onChange={(event) => setCode(event.target.value)} placeholder="短信验证码" onPressEnter={submitCode} />
            <Button type="primary" onClick={submitCode}>提交验证码</Button>
          </Space.Compact>}
          {!terminalLoginStates.has(loginSession.status) && <Button danger onClick={cancelLogin}>取消登录</Button>}
          {loginSession.error_message && <Typography.Text type="danger">{loginSession.error_message}</Typography.Text>}
        </Space>}
      </Modal>
    </div>
  );
}

function Creators() {
  const [rows, setRows] = useState<Creator[]>([]);
  const [detail, setDetail] = useState<Creator>();
  const [filters, setFilters] = useState<Record<string, string | number | undefined>>({});
  const platforms = useMemo(() => ['xingtu', 'ks_feigua', 'magnetic_juxing', 'huohua', 'feigua', 'merged'], []);
  const load = () => api.get('/creators', { params: filters }).then((res) => setRows(res.data));
  useEffect(() => { void load(); }, []);
  const showDetail = async (row: Creator) => {
    const res = await api.get(`/creators/${row.platform}/${encodeURIComponent(row.platform_creator_id)}`);
    setDetail(res.data);
  };
  return (
    <div className="panel">
      <Space className="toolbar filter-bar" wrap>
        <Select allowClear placeholder="平台" className="select" onChange={(platform) => setFilters((value) => ({ ...value, platform }))} options={platforms.map((p) => ({ value: p, label: p }))} />
        <Input placeholder="达人昵称" onChange={(event) => setFilters((value) => ({ ...value, q: event.target.value || undefined }))} />
        <InputNumber min={0} placeholder="最低粉丝" onChange={(minFollowers) => setFilters((value) => ({ ...value, min_followers: minFollowers ?? undefined }))} />
        <Input placeholder="省份" onChange={(event) => setFilters((value) => ({ ...value, province: event.target.value || undefined }))} />
        <Input placeholder="城市" onChange={(event) => setFilters((value) => ({ ...value, city: event.target.value || undefined }))} />
        <Input placeholder="来源文件" onChange={(event) => setFilters((value) => ({ ...value, source: event.target.value || undefined }))} />
        <Button type="primary" icon={<SearchOutlined />} onClick={load}>查询</Button>
      </Space>
      <Table
        rowKey={(row) => `${row.platform}:${row.platform_creator_id}:${row.id}`}
        dataSource={rows}
        scroll={{ x: 1050 }}
        onRow={(row) => ({ onDoubleClick: () => showDetail(row) })}
        columns={[
          { title: '平台', dataIndex: 'platform', width: 140 },
          { title: '达人 ID', dataIndex: 'platform_creator_id', width: 180 },
          { title: '昵称', dataIndex: 'nick_name' },
          { title: '粉丝', dataIndex: 'follower_count', width: 130 },
          { title: '省份', dataIndex: 'province', width: 110 },
          { title: '城市', dataIndex: 'city', width: 110 },
          { title: '来源', dataIndex: 'source_file', ellipsis: true },
          { title: '操作', width: 70, fixed: 'right', render: (_: unknown, row: Creator) => <Button aria-label="查看达人" title="查看达人" size="small" icon={<EyeOutlined />} onClick={() => showDetail(row)} /> }
        ]}
      />
      <Modal title={detail?.nick_name || detail?.platform_creator_id} open={Boolean(detail)} width={820} footer={null} onCancel={() => setDetail(undefined)}>
        {detail && <>
          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="平台">{detail.platform}</Descriptions.Item>
            <Descriptions.Item label="达人 ID">{detail.platform_creator_id}</Descriptions.Item>
            <Descriptions.Item label="粉丝">{detail.follower_count ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="地域">{[detail.province, detail.city].filter(Boolean).join(' / ') || '-'}</Descriptions.Item>
            <Descriptions.Item label="来源" span={2}>{detail.source_file || '-'}</Descriptions.Item>
          </Descriptions>
          <pre className="json-block">{JSON.stringify(detail.attributes_json || detail.metrics_json || {}, null, 2)}</pre>
        </>}
      </Modal>
    </div>
  );
}
