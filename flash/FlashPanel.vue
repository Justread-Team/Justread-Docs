<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Circle, CircleCheck, CircleX, LoaderCircle } from '@lucide/vue'
import { ESPLoader, Transport } from 'esptool-js'
// spark-md5 does not publish its own TypeScript declarations.
// @ts-expect-error -- CommonJS package without declaration files.
import SparkMD5 from 'spark-md5'
import { VPButton } from 'vitepress/theme'

type SerialPortHandle = ConstructorParameters<typeof Transport>[0]
type SerialPortInfo = { usbVendorId?: number; usbProductId?: number }
type FirmwareAsset = { label: string; url: string; bytes: number; sha256?: string }
type ResourceAsset = FirmwareAsset & { blockBytes: number }
type DeviceFlashProfile = {
  chip: string
  flash_size: string
  flash_mode: string
  flash_freq: string
  erase_all: boolean
  partitions: Record<string, number>
}
type DeviceModel = {
  id: string
  display_name: string
  resource_path: string
  ota_manifest: string
  web_flash_manifest?: string
  flash: DeviceFlashProfile
}
type FlashImage = { kind: string; path: string; address: number | string; bytes: number; sha256: string }
type WebFlashManifest = {
  model_id: string
  chip: string
  flash_size: string
  flash_mode: string
  flash_freq: string
  erase_all: boolean
  files: FlashImage[]
  notes?: string
}
type FirmwareManifest = {
  model_id: string
  version: string
  flash: WebFlashManifest | null
  resources: { systemFont: ResourceAsset }
}
type FlashState =
  | 'start' | 'ready' | 'flashing' | 'complete' | 'error'
  | 'resources' | 'resource_importing' | 'resource_complete' | 'resource_error'
type BrowserSerialPort = SerialPortHandle & {
  open(options: { baudRate: number }): Promise<void>
  close(): Promise<void>
  readable: ReadableStream<Uint8Array> | null
  writable: WritableStream<Uint8Array> | null
  setSignals?(signals: { dataTerminalReady?: boolean; requestToSend?: boolean }): Promise<void>
}
type SerialApi = {
  requestPort(options: { filters: Array<{ usbVendorId: number; usbProductId: number }> }): Promise<SerialPortHandle>
}

const CLOUD_ORIGIN = 'https://cdn.xmoa.smn.icu'
const DOWNLOADS_PATH = '/downloads/'
const RESOURCE_BLOCK_BYTES = 16 * 1024
const deviceFilters = [{ usbVendorId: 0x303a, usbProductId: 0x1001 }]
const flashSteps = ['下载并校验分区镜像', '连接并识别设备', '写入清单分区', '回读校验分区', '复位设备']

const selectedDevice = ref<SerialPortHandle | null>(null)
const models = ref<DeviceModel[]>([])
const selectedModelId = ref('')
const errorMessage = ref('')
const connecting = ref(false)
const isBusy = ref(false)
const flashState = ref<FlashState>('start')
const activeStepIndex = ref(0)
const progress = ref(0)
const status = ref('')
const pendingFirmwareName = ref('')
const confirmDialog = ref<HTMLDialogElement | null>(null)
const manifest = ref<FirmwareManifest | null>(null)
const manifestLoading = ref(true)
const manifestError = ref('')
const resourceProgress = ref(0)
const resourceStatus = ref('')
const resourceError = ref('')
const resourceResult = ref<'installed' | 'already' | 'not-needed' | ''>('')
let resolveFlashConfirmation: ((confirmed: boolean) => void) | null = null
let activeTransport: Transport | null = null
let manifestRequest = 0

const selectedModel = computed(() => models.value.find((model) => model.id === selectedModelId.value) ?? null)
const firmwareName = computed(() => {
  if (!selectedModel.value) return 'JustRead'
  return `${selectedModel.value.display_name} · JustRead${manifest.value?.version ? ` ${manifest.value.version}` : ''}`
})
const canFlash = computed(() => Boolean(manifest.value?.flash?.files.length))
const resourceCompletionText = computed(() => {
  if (resourceResult.value === 'already') return '设备已有有效系统字体，请继续在设备屏幕完成首次启动引导。'
  if (resourceResult.value === 'not-needed') return '设备当前不需要导入首次启动资源。'
  return '系统字体已写入设备 SD 卡。请在设备屏幕上选择登录或注册云账户，或暂不使用并进入书架。'
})

onMounted(() => { void loadModels() })
onBeforeUnmount(() => { settleFlashConfirmation(false) })

function cloudDownloadUrl(path: string) {
  if (!path.startsWith(DOWNLOADS_PATH) || path.includes('..')) throw new Error('Cloud 下载路径无效。')
  const url = new URL(path, CLOUD_ORIGIN)
  if (url.origin !== CLOUD_ORIGIN || !url.pathname.startsWith(DOWNLOADS_PATH)) throw new Error('Cloud 下载路径无效。')
  return url.toString()
}

function isDeviceModel(value: unknown): value is DeviceModel {
  if (!value || typeof value !== 'object') return false
  const model = value as Partial<DeviceModel>
  const flash = model.flash
  return typeof model.id === 'string' && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(model.id)
    && typeof model.display_name === 'string' && model.display_name.trim().length > 0
    && model.resource_path === `${DOWNLOADS_PATH}${model.id}/`
    && model.ota_manifest === `${model.resource_path}release.json`
    && (model.web_flash_manifest === undefined || model.web_flash_manifest === `${model.resource_path}web-flash.json`)
    && !!flash && typeof flash.chip === 'string' && typeof flash.flash_size === 'string'
    && typeof flash.flash_mode === 'string' && typeof flash.flash_freq === 'string'
    && flash.erase_all === false && !!flash.partitions && typeof flash.partitions === 'object'
    && !Array.isArray(flash.partitions) && Object.keys(flash.partitions).length > 0
    && Object.values(flash.partitions).every((address) => Number.isSafeInteger(address) && address >= 0)
}

function isAsset(value: unknown, expectedPath?: string): value is { path: string; bytes: number; sha256: string } {
  if (!value || typeof value !== 'object') return false
  const asset = value as Partial<{ path: string; bytes: number; sha256: string }>
  if (typeof asset.path !== 'string' || !asset.path.startsWith(DOWNLOADS_PATH) || asset.path.includes('..')) return false
  if (expectedPath && asset.path !== expectedPath) return false
  if (!Number.isSafeInteger(asset.bytes) || (asset.bytes ?? 0) <= 0 || typeof asset.sha256 !== 'string' || !/^[a-f0-9]{64}$/i.test(asset.sha256)) return false
  try { cloudDownloadUrl(asset.path) } catch { return false }
  return true
}

function parseAddress(value: number | string) {
  return typeof value === 'number' ? value : Number(value)
}

function flashCapacityBytes(value: string) {
  const match = /^(\d+)(?:MB|MiB)$/i.exec(value)
  return match ? Number(match[1]) * 1024 * 1024 : 0
}

function imageLabel(kind: string) {
  const labels: Record<string, string> = {
    bootloader: 'Bootloader',
    partition_table: '分区表',
    ota_data: 'OTA 启动数据',
    application: 'JustRead 应用',
  }
  return labels[kind] ?? kind
}

function validWebFlashManifest(value: unknown, model: DeviceModel): value is WebFlashManifest {
  if (!value || typeof value !== 'object') return false
  const item = value as Partial<WebFlashManifest>
  const expected = model.flash.partitions
  const capacity = flashCapacityBytes(model.flash.flash_size)
  if (item.model_id !== model.id || item.chip !== model.flash.chip || item.flash_size !== model.flash.flash_size
      || item.flash_mode !== model.flash.flash_mode || item.flash_freq !== model.flash.flash_freq
      || item.erase_all !== false || !capacity || !Array.isArray(item.files)
      || item.files.length !== Object.keys(expected).length
      || (item.notes !== undefined && (typeof item.notes !== 'string' || item.notes.length > 300))) return false
  const kinds = new Set<string>()
  const paths = new Set<string>()
  for (const file of item.files) {
    if (!file || typeof file.kind !== 'string' || !Object.hasOwn(expected, file.kind)
        || kinds.has(file.kind)
        || !(typeof file.address === 'number' || (typeof file.address === 'string' && /^0x[0-9a-f]+$/i.test(file.address)))
        || parseAddress(file.address) !== expected[file.kind]
        || typeof file.path !== 'string' || !file.path.startsWith(model.resource_path)
        || file.path.includes('..') || paths.has(file.path)
        || !Number.isSafeInteger(file.bytes) || file.bytes <= 0
        || typeof file.sha256 !== 'string' || !/^[a-f0-9]{64}$/i.test(file.sha256)) return false
    const address = parseAddress(file.address)
    if (address + file.bytes > capacity) return false
    const nextPartition = Object.values(expected).filter((next) => next > address).sort((left, right) => left - right)[0]
    if (nextPartition !== undefined && address + file.bytes > nextPartition) return false
    try { cloudDownloadUrl(file.path) } catch { return false }
    kinds.add(file.kind)
    paths.add(file.path)
  }
  return kinds.size === Object.keys(expected).length
}

async function loadModels() {
  manifestLoading.value = true
  manifestError.value = ''
  manifest.value = null
  try {
    const response = await fetch(`${CLOUD_ORIGIN}${DOWNLOADS_PATH}models.json`, { cache: 'no-store' })
    if (!response.ok) throw new Error(`Cloud 型号清单读取失败（HTTP ${response.status}）。`)
    const catalog: unknown = await response.json()
    if (!catalog || typeof catalog !== 'object') throw new Error('Cloud 型号清单格式无效。')
    const value = catalog as { schema_version?: unknown; models?: unknown }
    if (value.schema_version !== 1 || !Array.isArray(value.models) || !value.models.length || !value.models.every(isDeviceModel)) {
      throw new Error('Cloud 型号清单格式无效。')
    }
    const loadedModels = value.models as DeviceModel[]
    if (new Set(loadedModels.map((model) => model.id)).size !== loadedModels.length) throw new Error('Cloud 型号清单包含重复型号。')
    models.value = loadedModels
    if (!loadedModels.some((model) => model.id === selectedModelId.value)) selectedModelId.value = loadedModels[0].id
    await loadManifest()
  } catch {
    manifestError.value = '刷机信息加载失败，请刷新网页重试。'
    models.value = []
    manifest.value = null
  } finally {
    manifestLoading.value = false
  }
}

async function loadManifest() {
  const request = ++manifestRequest
  const model = selectedModel.value
  manifestLoading.value = true
  manifestError.value = ''
  manifest.value = null
  if (!model) {
    manifestLoading.value = false
    return
  }
  try {
    const requests = [fetch(cloudDownloadUrl(model.ota_manifest), { cache: 'no-store' })]
    if (model.web_flash_manifest) requests.push(fetch(cloudDownloadUrl(model.web_flash_manifest), { cache: 'no-store' }))
    const responses = await Promise.all(requests)
    if (!responses[0].ok) throw new Error(`Cloud 发布清单读取失败（HTTP ${responses[0].status}）。`)
    const releaseValue: unknown = await responses[0].json()
    if (!releaseValue || typeof releaseValue !== 'object') throw new Error('Cloud 发布清单格式无效。')
    const release = releaseValue as {
      model_id?: unknown; version?: unknown; firmware?: unknown; system_font?: unknown
    }
    if (release.model_id !== model.id || typeof release.version !== 'string' || !release.version
        || !isAsset(release.firmware, `${model.resource_path}firmware.bin`)
        || !isAsset(release.system_font, `${DOWNLOADS_PATH}shared/system.ttf`)) {
      throw new Error('Cloud 发布清单与型号不匹配。')
    }
    let flash: WebFlashManifest | null = null
    if (model.web_flash_manifest) {
      if (!responses[1].ok) throw new Error(`Cloud 分区刷机清单读取失败（HTTP ${responses[1].status}）。`)
      const flashValue: unknown = await responses[1].json()
      if (!validWebFlashManifest(flashValue, model)) throw new Error('分区刷机清单与设备型号的地址布局不匹配。')
      flash = flashValue
      const application = flash.files.find((file) => file.kind === 'application')
      const firmware = release.firmware
      if (!application || !isAsset(firmware, `${model.resource_path}firmware.bin`)
          || application.path !== firmware.path || application.bytes !== firmware.bytes
          || application.sha256.toLowerCase() !== firmware.sha256.toLowerCase()) {
        throw new Error('网页刷机应用镜像与 OTA 发布清单不一致。')
      }
    }
    if (request !== manifestRequest) return
    const font = release.system_font
    manifest.value = {
      model_id: model.id,
      version: release.version,
      flash,
      resources: {
        systemFont: {
          label: 'JustRead 系统字体',
          url: cloudDownloadUrl(font.path),
          bytes: font.bytes,
          sha256: font.sha256,
          blockBytes: RESOURCE_BLOCK_BYTES,
        },
      },
    }
  } catch {
    if (request === manifestRequest) manifestError.value = '刷机信息加载失败，请刷新网页重试。'
  } finally {
    if (request === manifestRequest) manifestLoading.value = false
  }
}

function changeModel(event: Event) {
  if (isBusy.value || connecting.value) return
  const nextModelId = (event.target as HTMLSelectElement).value
  if (!models.value.some((model) => model.id === nextModelId) || nextModelId === selectedModelId.value) return
  selectedModelId.value = nextModelId
  selectedDevice.value = null
  flashState.value = 'start'
  errorMessage.value = ''
  void loadManifest()
}

function getSerialApi() {
  return (navigator as Navigator & { serial?: SerialApi }).serial
}

async function connectDevice() {
  if (connecting.value || isBusy.value) return
  errorMessage.value = ''
  const serial = getSerialApi()
  if (!window.isSecureContext || !serial) {
    errorMessage.value = '请使用 HTTPS 下的 Chrome 或 Edge。'
    return
  }
  connecting.value = true
  try {
    const port = await serial.requestPort({ filters: deviceFilters })
    const info = (port as SerialPortHandle & { getInfo: () => SerialPortInfo }).getInfo()
    if (info.usbVendorId !== 0x303a || info.usbProductId !== 0x1001) {
      throw new Error('请选择通过 USB 连接的小纸 Pico。')
    }
    selectedDevice.value = port
    flashState.value = 'ready'
  } catch (error) {
    if (!(error instanceof DOMException && error.name === 'NotFoundError')) {
      errorMessage.value = error instanceof Error ? error.message : '无法选择设备，请检查 USB 连接后重试。'
    }
  } finally {
    connecting.value = false
  }
}

function sha256(data: Uint8Array) {
  return crypto.subtle.digest('SHA-256', data).then((digest) =>
    Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join(''),
  )
}

function md5(data: Uint8Array) {
  return SparkMD5.ArrayBuffer.hash(data.buffer)
}

async function fetchVerifiedAsset(asset: FirmwareAsset, label: string) {
  const response = await fetch(asset.url, { cache: 'no-store' })
  if (!response.ok) throw new Error(label + '下载失败。')
  const data = new Uint8Array(await response.arrayBuffer())
  if (data.byteLength !== asset.bytes) throw new Error(label + '文件大小校验失败。')
  if (asset.sha256?.trim() && await sha256(data) !== asset.sha256.trim().toLowerCase()) {
    throw new Error(label + ' SHA-256 校验失败。')
  }
  return data
}

function confirmPartitionFlash() {
  return new Promise<boolean>((resolve) => {
    const dialog = confirmDialog.value
    if (!dialog) return resolve(false)
    resolveFlashConfirmation = resolve
    dialog.showModal()
  })
}

function settleFlashConfirmation(confirmed: boolean) {
  resolveFlashConfirmation?.(confirmed)
  resolveFlashConfirmation = null
  confirmDialog.value?.close()
}

async function startFlashing() {
  const port = selectedDevice.value
  const flashManifest = manifest.value?.flash
  const model = selectedModel.value
  if (isBusy.value || connecting.value || !port || !flashManifest || !model) return
  pendingFirmwareName.value = firmwareName.value
  const targetFirmwareName = pendingFirmwareName.value
  isBusy.value = true
  try {
    if (!(await confirmPartitionFlash())) return
    flashState.value = 'flashing'
    errorMessage.value = ''
    activeStepIndex.value = 0
    progress.value = 0
    status.value = '下载并校验分区镜像…'
    const images = await Promise.all(flashManifest.files.map(async (file) => {
      const label = imageLabel(file.kind)
      status.value = `下载并校验 ${label}…`
      const data = await fetchVerifiedAsset({
        label,
        url: cloudDownloadUrl(file.path),
        bytes: file.bytes,
        sha256: file.sha256,
      }, label)
      return { data, address: parseAddress(file.address), kind: file.kind }
    }))
    images.sort((left, right) => left.address - right.address)
    activeStepIndex.value = 1
    status.value = `连接并识别 ${flashManifest.chip}…`
    const terminal = { clean() {}, writeLine(_data: string) {}, write(_data: string) {} }
    activeTransport = new Transport(port, false)
    const loader = new ESPLoader({ transport: activeTransport, baudrate: 460800, romBaudrate: 115200, terminal })
    const chipName = await loader.main()
    if (!chipName.toUpperCase().includes(flashManifest.chip.toUpperCase())) {
      throw new Error(`检测到 ${chipName}，目标设备芯片必须是 ${flashManifest.chip}。`)
    }
    if (await loader.detectFlashSize() !== flashManifest.flash_size) {
      throw new Error(`设备 Flash 容量与清单要求的 ${flashManifest.flash_size} 不符，未写入设备。`)
    }

    activeStepIndex.value = 2
    status.value = '写入清单列出的分区…'
    const sizes = images.map((image) => image.data.byteLength)
    const written = sizes.map(() => 0)
    const total = sizes.reduce((sum, size) => sum + size, 0)
    await loader.writeFlash({
      fileArray: images.map((image) => ({ data: image.data, address: image.address })),
      flashMode: flashManifest.flash_mode,
      flashFreq: flashManifest.flash_freq,
      flashSize: flashManifest.flash_size,
      eraseAll: false,
      compress: true,
      reportProgress: (fileIndex, bytesWritten) => {
        if (fileIndex < 0 || fileIndex >= written.length) return
        written[fileIndex] = Math.min(sizes[fileIndex], bytesWritten)
        progress.value = total ? Math.floor(written.reduce((sum, size) => sum + size, 0) / total * 100) : 0
        status.value = `正在写入 ${imageLabel(images[fileIndex].kind)}…`
      },
    })
    activeStepIndex.value = 3
    progress.value = 0
    status.value = '回读校验分区…'
    let verifiedBytes = 0
    for (const image of images) {
      if (await loader.flashMd5sum(image.address, image.data.byteLength) !== md5(image.data)) {
        throw new Error(`${imageLabel(image.kind)} 回读校验失败，请保持 USB 连接并重试。`)
      }
      verifiedBytes += image.data.byteLength
      progress.value = total ? Math.floor(verifiedBytes / total * 100) : 100
    }
    activeStepIndex.value = 4
    status.value = '复位设备…'
    await loader.after('custom_reset', false, 'R1|W100|R0')
    activeStepIndex.value = flashSteps.length
    progress.value = 100
    resourceStatus.value = '固件已刷写完成。请重新连接设备并导入首次启动资源。'
    flashState.value = 'resources'
    status.value = targetFirmwareName + '刷写完成。'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '刷写失败，请保持 USB 连接并重试。'
    flashState.value = 'error'
    status.value = ''
  } finally {
    try { await activeTransport?.disconnect() } catch { /* USB may disconnect after reset. */ }
    if (activeTransport) selectedDevice.value = null
    activeTransport = null
    isBusy.value = false
  }
}

function returnToSelection() {
  if (isBusy.value) return
  errorMessage.value = ''
  flashState.value = selectedDevice.value ? 'ready' : 'start'
  activeStepIndex.value = 0
  progress.value = 0
  status.value = ''
  resourceStatus.value = ''
  resourceError.value = ''
  resourceProgress.value = 0
  resourceResult.value = ''
}

function openResourceImport() {
  if (isBusy.value || connecting.value) return
  selectedDevice.value = null
  flashState.value = 'resources'
  resourceStatus.value = ''
  resourceError.value = ''
  resourceProgress.value = 0
  resourceResult.value = ''
}

type SerialLineReader = {
  waitFor(match: (line: string) => boolean, timeoutMs: number): Promise<string>
  stop(): Promise<void>
}

function readSerialLines(stream: ReadableStream<Uint8Array>): SerialLineReader {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  const queued: string[] = []
  const waiters: Array<{
    match: (line: string) => boolean
    resolve: (line: string) => void
    reject: (error: Error) => void
    timer: ReturnType<typeof setTimeout>
  }> = []
  let buffer = ''
  let stopped = false

  const rejectWaiters = (error: Error) => {
    for (const waiter of waiters.splice(0)) {
      clearTimeout(waiter.timer)
      waiter.reject(error)
    }
  }

  const dispatch = (line: string) => {
    for (let index = waiters.length - 1; index >= 0; index--) {
      const waiter = waiters[index]
      if (waiter.match(line)) {
        waiters.splice(index, 1)
        clearTimeout(waiter.timer)
        waiter.resolve(line)
        return
      }
    }
    queued.push(line)
    if (queued.length > 500) queued.shift()
  }

  const pump = (async () => {
    try {
      while (!stopped) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split(/\r?\n/)
        buffer = parts.pop() ?? ''
        for (const line of parts) dispatch(line)
      }
      rejectWaiters(new Error('设备串口已关闭。'))
    } catch (error) {
      rejectWaiters(error instanceof Error ? error : new Error('设备串口读取失败。'))
    } finally {
      try { reader.releaseLock() } catch { /* stream already released */ }
    }
  })()

  return {
    waitFor(match, timeoutMs) {
      const foundIndex = queued.findIndex(match)
      if (foundIndex >= 0) return Promise.resolve(queued.splice(foundIndex, 1)[0])
      if (stopped) return Promise.reject(new Error('设备串口已关闭。'))
      return new Promise((resolve, reject) => {
        const waiter = {
          match,
          resolve,
          reject,
          timer: setTimeout(() => {
            const index = waiters.indexOf(waiter)
            if (index >= 0) waiters.splice(index, 1)
            reject(new Error('等待设备响应超时，请检查 USB 连接后重试。'))
          }, timeoutMs),
        }
        waiters.push(waiter)
      })
    },
    async stop() {
      stopped = true
      try { await reader.cancel() } catch { /* device may already be disconnected */ }
      await pump.catch(() => undefined)
    },
  }
}

function responseWaiter(match: (line: string) => boolean) {
  return (line: string) => line.includes('JR_UPLOAD_ERROR') || match(line)
}

async function sendCommand(
  writer: WritableStreamDefaultWriter<Uint8Array>,
  lines: SerialLineReader,
  command: string,
  match: (line: string) => boolean,
  timeoutMs = 15000,
) {
  await writer.write(new TextEncoder().encode(command + '\n'))
  const line = await lines.waitFor(responseWaiter(match), timeoutMs)
  if (line.includes('JR_UPLOAD_ERROR')) throw new Error('设备拒绝资源导入：' + line)
  return line
}

function parseResourceStatus(line: string) {
  return Object.fromEntries(
    Array.from(line.matchAll(/(phase|first|required|valid|busy|error|done|total)=(-?\d+)/g), ([, key, value]) => [key, Number(value)]),
  ) as Record<string, number>
}

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function startResourceImport() {
  if (isBusy.value || !manifest.value) return
  const serial = getSerialApi()
  if (!window.isSecureContext || !serial) {
    flashState.value = 'resource_error'
    resourceError.value = '请使用 HTTPS 下的 Chrome 或 Edge。'
    return
  }

  // requestPort must be called directly from this button gesture.
  const portPromise = serial.requestPort({ filters: deviceFilters })
  isBusy.value = true
  flashState.value = 'resource_importing'
  resourceStatus.value = '连接设备…'
  resourceError.value = ''
  resourceProgress.value = 0
  resourceResult.value = ''

  let port: BrowserSerialPort | null = null
  let writer: WritableStreamDefaultWriter<Uint8Array> | null = null
  let lines: SerialLineReader | null = null
  try {
    port = await portPromise as BrowserSerialPort
    const info = (port as SerialPortHandle & { getInfo: () => { usbVendorId?: number; usbProductId?: number } }).getInfo()
    if (info.usbVendorId !== 0x303a || info.usbProductId !== 0x1001) {
      throw new Error('请选择通过 USB 连接的小纸 Pico。')
    }
    await port.open({ baudRate: 115200 })
    await port.setSignals?.({ dataTerminalReady: false, requestToSend: false })
    if (!port.readable || !port.writable) throw new Error('设备串口不可读写。')
    lines = readSerialLines(port.readable)
    writer = port.writable.getWriter()

    const getStatus = async () => {
      const line = await sendCommand(writer!, lines!, 'jr resources status', (text) => text.includes('JR_RESOURCE_STATUS:'), 15000)
      return parseResourceStatus(line)
    }
    resourceStatus.value = '检查设备资源状态…'
    let deviceStatus = await getStatus()
    const statusDeadline = Date.now() + 120000
    while (deviceStatus.busy === 1) {
      if (Date.now() > statusDeadline) throw new Error('设备资源检查超时，请稍后重试。')
      await wait(500)
      deviceStatus = await getStatus()
    }

    if (deviceStatus.valid === 1) {
      resourceResult.value = 'already'
      flashState.value = 'resource_complete'
      return
    }
    if (deviceStatus.required !== 1) {
      resourceResult.value = 'not-needed'
      flashState.value = 'resource_complete'
      return
    }
    if (deviceStatus.phase === 1) {
      throw new Error('设备尚未检测到 SD 卡。插入 SD 卡后，在设备上点“重新检查”，再重新导入。')
    }
    while (deviceStatus.phase !== 2 && deviceStatus.phase !== 7) {
      if (Date.now() > statusDeadline) throw new Error('等待设备检查 SD 卡超时。')
      await wait(500)
      deviceStatus = await getStatus()
      if (deviceStatus.valid === 1 || deviceStatus.required !== 1) {
        resourceResult.value = deviceStatus.valid === 1 ? 'already' : 'not-needed'
        flashState.value = 'resource_complete'
        return
      }
      if (deviceStatus.phase === 1) {
        throw new Error('设备尚未检测到 SD 卡。插入 SD 卡后，在设备上点“重新检查”，再重新导入。')
      }
    }

    const font = manifest.value.resources.systemFont
    resourceStatus.value = '下载系统字体…'
    const fontData = await fetchVerifiedAsset(font, font.label)
    // The device requires its pinned resource digest even when development JSON omits one.
    const fontDigest = font.sha256?.trim() || await sha256(fontData)
    resourceStatus.value = '开始向设备发送系统字体…'
    await sendCommand(writer, lines, 'jr resources begin ' + font.bytes + ' ' + fontDigest + ' ' + font.blockBytes, (text) => text.includes('JR_UPLOAD_BEGIN:'), 30000)

    for (let offset = 0; offset < fontData.byteLength; offset += font.blockBytes) {
      const end = Math.min(fontData.byteLength, offset + font.blockBytes)
      await writer.write(fontData.subarray(offset, end))
      const sent = end
      const ack = await lines.waitFor(
        responseWaiter((text) => text.includes('JR_UPLOAD_ACK: bytes=' + sent)),
        30000,
      )
      if (ack.includes('JR_UPLOAD_ERROR')) throw new Error('设备写入失败：' + ack)
      resourceProgress.value = Math.floor((sent / fontData.byteLength) * 100)
      resourceStatus.value = '写入系统字体 ' + resourceProgress.value + '%'
    }

    resourceStatus.value = '设备正在校验并保存系统字体…'
    const done = await lines.waitFor(responseWaiter((text) => text.includes('JR_UPLOAD_DONE:')), 180000)
    if (done.includes('JR_UPLOAD_ERROR')) throw new Error('设备资源写入失败：' + done)
    resourceProgress.value = 100
    resourceResult.value = 'installed'
    flashState.value = 'resource_complete'
    resourceStatus.value = '资源已写入。'
  } catch (error) {
    flashState.value = 'resource_error'
    resourceError.value = error instanceof Error ? error.message : '资源导入失败，请保持 USB 连接后重试。'
  } finally {
    try { await lines?.stop() } catch { /* device may have reset */ }
    try { writer?.releaseLock() } catch { /* stream may have closed */ }
    if (port) {
      try { await port.close() } catch { /* already closed */ }
    }
    isBusy.value = false
  }
}
</script>

<template>
  <main class="flash-page">
    <h1>在线刷机</h1>
    <section class="flash-panel" aria-live="polite" aria-atomic="true">
      <div
        v-if="flashState === 'resources' || flashState === 'resource_importing' || flashState === 'resource_complete' || flashState === 'resource_error'"
        class="selection-form"
      >
        <p class="flash-status">{{ flashState === 'resource_complete' ? '首次启动资源已就绪' : '导入首次启动资源' }}</p>
        <p v-if="flashState === 'resource_complete'">{{ resourceCompletionText }}</p>
        <template v-else>
          <p>首次启动需要系统字体。请插入设备 SD 卡并通过 USB 连接设备。</p>
          <VPButton
            :text="isBusy ? '正在导入…' : '通过 USB 导入资源'"
            size="big"
            :disabled="isBusy || !manifest"
            @click="startResourceImport"
          />
        </template>
        <div v-if="resourceStatus" class="step-row">
          <LoaderCircle v-if="isBusy" class="step-icon spinning" aria-hidden="true" />
          <CircleCheck v-else-if="flashState === 'resource_complete'" class="step-icon" aria-hidden="true" />
          <Circle v-else class="step-icon" aria-hidden="true" />
          <span>{{ resourceStatus }}</span>
          <span v-if="flashState === 'resource_importing' && resourceProgress > 0" class="step-percent">{{ resourceProgress }}%</span>
        </div>
        <div v-if="flashState === 'resource_importing' && resourceProgress > 0" class="progress-track" role="progressbar" :aria-valuenow="resourceProgress" aria-valuemin="0" aria-valuemax="100" aria-label="系统字体导入">
          <div class="progress-value" :style="{ width: `${resourceProgress}%` }" />
        </div>
        <p v-if="resourceError" class="connection-error" role="alert">{{ resourceError }}</p>
        <VPButton text="返回设备选择" theme="alt" :disabled="isBusy" @click="returnToSelection" />
      </div>
      <div v-else-if="flashState === 'flashing' || flashState === 'complete' || flashState === 'error'" class="flash-progress">
        <p class="flash-status">{{ flashState === 'complete' ? '刷机完成' : flashState === 'error' ? '刷写失败' : '正在烧录' + pendingFirmwareName + '…' }}</p>
        <p v-if="status">{{ status }}</p>
        <ol class="flash-steps">
          <li
            v-for="(step, index) in flashSteps"
            :key="step"
            class="flash-step"
            :class="{
              'is-complete': index < activeStepIndex || flashState === 'complete',
              'is-active': index === activeStepIndex && flashState !== 'complete',
              'is-error': index === activeStepIndex && flashState === 'error',
            }"
          >
            <div class="step-row">
              <CircleCheck v-if="index < activeStepIndex || flashState === 'complete'" class="step-icon" aria-hidden="true" />
              <CircleX v-else-if="index === activeStepIndex && flashState === 'error'" class="step-icon" aria-hidden="true" />
              <LoaderCircle v-else-if="index === activeStepIndex && flashState === 'flashing'" class="step-icon spinning" aria-hidden="true" />
              <Circle v-else class="step-icon" aria-hidden="true" />
              <span>{{ step }}</span>
              <span v-if="index === activeStepIndex && (index === 2 || index === 3) && flashState === 'flashing'" class="step-percent">
                {{ progress }}%
              </span>
            </div>
            <div v-if="index === activeStepIndex && (index === 2 || index === 3) && flashState === 'flashing'" class="progress-track" role="progressbar" :aria-valuenow="progress" aria-valuemin="0" aria-valuemax="100" :aria-label="step">
              <div class="progress-value" :style="{ width: `${progress}%` }" />
            </div>
          </li>
        </ol>
        <p v-if="flashState === 'error'" class="connection-error" role="alert">{{ errorMessage }}</p>
        <VPButton v-if="flashState === 'error'" text="返回设备选择" theme="alt" @click="returnToSelection" />
        <VPButton v-if="flashState === 'complete'" text="返回" theme="alt" @click="returnToSelection" />
      </div>

      <div v-else class="selection-form">
        <label class="field-label" for="device-model">设备型号</label>
        <select id="device-model" :value="selectedModelId" :disabled="isBusy || connecting || manifestLoading" @change="changeModel">
          <option v-for="device in models" :key="device.id" :value="device.id">
            {{ device.display_name }}
          </option>
        </select>
        <div v-if="selectedModel" class="device-meta" aria-label="设备固件信息">
          <div class="device-meta-row">
            <span class="device-meta-label">设备型号</span>
            <span class="device-meta-value">
              <span>{{ selectedModel.display_name }}</span>
              <code>{{ selectedModel.id }}</code>
            </span>
          </div>
          <div class="device-meta-row">
            <span class="device-meta-label">JustRead 版本</span>
            <code class="device-meta-value">{{ manifest?.version ?? (manifestLoading ? '读取中…' : '—') }}</code>
          </div>
        </div>
        <p v-if="selectedModel && !selectedModel.web_flash_manifest" class="connection-error" role="status">
          此型号尚未发布网页刷机分区清单。
        </p>
        <VPButton
          :text="isBusy ? '等待确认…' : connecting ? '正在连接…' : selectedDevice ? '开始刷机' : '连接设备'"
          size="big"
          :disabled="isBusy || connecting || !canFlash"
          @click="selectedDevice ? startFlashing() : connectDevice()"
        />
        <VPButton text="资源导入" theme="alt" :disabled="isBusy || connecting || !manifest" @click="openResourceImport" />
        <p v-if="manifestLoading">正在从 Cloud 读取型号和资源清单…</p>
        <p v-if="manifestError" class="connection-error" role="alert">{{ manifestError }}</p>
        <p v-if="errorMessage" class="connection-error" role="alert">{{ errorMessage }}</p>
      </div>
    </section>

    <dialog
      ref="confirmDialog"
      class="flash-confirm-dialog"
      aria-labelledby="flash-confirm-title"
      @cancel.prevent="settleFlashConfirmation(false)"
      @click.self="settleFlashConfirmation(false)"
    >
      <h2 id="flash-confirm-title" class="flash-confirm-title">确认刷写 {{ pendingFirmwareName }}</h2>
      <div class="dialog-actions">
        <VPButton text="取消" theme="alt" @click="settleFlashConfirmation(false)" />
        <VPButton text="确定" @click="settleFlashConfirmation(true)" />
      </div>
    </dialog>
  </main>
</template>

<style scoped>
.flash-page {
  box-sizing: border-box;
  display: grid;
  width: 100%;
  margin-inline: auto;
  align-content: start;
  justify-items: center;
  padding: max(2rem, env(safe-area-inset-top))
    max(1.5rem, env(safe-area-inset-right))
    max(2rem, env(safe-area-inset-bottom))
    max(1.5rem, env(safe-area-inset-left));
}

.flash-panel {
  box-sizing: border-box;
  display: grid;
  width: min(100%, 28rem);
  gap: 1.25rem;
  padding: 2rem;
  text-align: left;
}

.flash-page > h1 {
  border: 0;
}

.flash-confirm-dialog {
  box-sizing: border-box;
  position: fixed;
  inset: 50% auto auto 50%;
  width: min(calc(100vw - 2rem), 32rem);
  max-height: calc(100vh - 2rem);
  margin: 0;
  overflow-y: auto;
  transform: translate(-50%, -50%);
  padding: 1rem;
  border: 0;
  border-radius: 12px;
  background: var(--vp-c-bg);
  color: var(--vp-c-text-1);
  box-shadow: var(--vp-shadow-3);
}

.flash-confirm-dialog::backdrop {
  background: rgb(0 0 0 / 55%);
}

.flash-confirm-dialog #flash-confirm-title {
  margin: 0;
  border: 0;
  padding: 0;
  font: inherit;
  font-weight: 600;
  line-height: 1.4;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.selection-form {
  display: grid;
  gap: 0.625rem;
}

.selection-form select {
  width: 100%;
  min-height: 2.5rem;
  border: 1px solid var(--vp-c-divider);
  border-radius: 10px;
  background-color: var(--vp-c-bg-soft);
  color: var(--vp-c-text-1);
  padding: 0.25rem 1rem;
  appearance: auto;
  -webkit-appearance: menulist;
}

.device-meta {
  display: grid;
  gap: 0.625rem;
  padding: 0.75rem;
  border-radius: 10px;
  background: var(--vp-c-bg-soft);
}

.device-meta-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  font-size: 0.9rem;
}

.device-meta-label {
  flex: none;
  color: var(--vp-c-text-2);
}

.device-meta-value {
  display: grid;
  justify-items: end;
  gap: 0.15rem;
  min-width: 0;
  text-align: right;
  overflow-wrap: anywhere;
}

.field-label {
  color: var(--vp-c-text-2);
  font-weight: 600;
}

.flash-status {
  margin: 0 0 1rem;
  border: 0;
  padding: 0;
  color: var(--vp-c-text-1);
  font-weight: 600;
  line-height: 1.35;
  text-align: center;
}

.flash-steps {
  margin: 0;
  padding: 0;
  list-style: none;
}

.flash-step {
  padding: 1rem 0;
  color: var(--vp-c-text-3);
}

.flash-step.is-complete {
  color: var(--vp-c-text-2);
}

.flash-step.is-active {
  color: var(--vp-c-text-1);
}

.flash-step.is-error {
  color: var(--vp-c-danger-1);
}

.step-row {
  display: grid;
  grid-template-columns: 1.5rem minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.75rem;
}

.step-icon {
  width: 1.375rem;
  height: 1.375rem;
  color: var(--vp-c-text-3);
}

.is-complete .step-icon {
  color: var(--vp-c-brand-1);
}

.is-active .step-icon {
  color: var(--vp-c-brand-1);
}

.is-error .step-icon {
  color: var(--vp-c-danger-1);
}

.step-percent {
  color: var(--vp-c-text-2);
  font-variant-numeric: tabular-nums;
}

.progress-track {
  height: 0.375rem;
  margin: 0.75rem 0 0 2.125rem;
  overflow: hidden;
  border-radius: 999px;
  background: var(--vp-c-bg-soft);
}

.progress-value {
  height: 100%;
  border-radius: inherit;
  background: var(--vp-c-brand-1);
  transition: width 150ms ease;
}

.connection-error {
  max-width: 28rem;
  margin: 0;
  color: var(--vp-c-danger-1);
}

.spinning {
  animation: spin 1s linear infinite;
}

@media (max-width: 480px) {
  .flash-panel {
    padding: 1.4rem;
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .spinning {
    animation-duration: 2s;
  }

  .progress-value {
    transition: none;
  }
}
</style>
