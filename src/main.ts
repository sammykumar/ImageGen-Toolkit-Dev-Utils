import { api } from '../../../scripts/api.js'
import { app } from '../../../scripts/app.js'

declare const __IMAGEGEN_TOOLKIT_BUILD_INFO__: {
	commitHash: string
	packageVersion: string
}

type WidgetLike = {
	name?: string
	value?: unknown
	callback?: (...args: unknown[]) => unknown
}

type DOMWidgetLike = {
	onRemove?: () => void
}

type LoadVideoPreviewState = {
	sync: () => void
	cleanup: () => void
}

type NodeLike = {
	widgets?: WidgetLike[]
	size?: [number, number]
	type?: string
	comfyClass?: string
	addDOMWidget?: (
		name: string,
		type: string,
		element: HTMLElement,
		options?: Record<string, unknown>
	) => DOMWidgetLike
	computeSize?: () => [number, number]
	setSize?: (size: [number, number]) => void
	setDirtyCanvas?: (dirtyForeground?: boolean, dirtyBackground?: boolean) => void
	onRemoved?: (...args: unknown[]) => unknown
	__loadVideoUrlPreviewState?: LoadVideoPreviewState
}

type GraphLike = {
	_nodes?: NodeLike[]
}

type NodeDefinitionLike = {
	name?: string
}

type NodeTypeLike = {
	prototype: NodeLike & {
		onNodeCreated?: (...args: unknown[]) => unknown
		onConfigure?: (...args: unknown[]) => unknown
	}
}

type ExtensionLike = {
	name: string
	setup?: () => void | Promise<void>
	beforeRegisterNodeDef?: (nodeType: NodeTypeLike, nodeData: NodeDefinitionLike) => void
}

type GraphToPromptResult = {
	output?: Record<string, unknown>
}

type LiveExportRequestDetail = {
	requestId?: string
}

type LiveExportSuccessPayload = {
	requestId: string
	ok: true
	apiPrompt: Record<string, unknown>
	clientId?: string
	graphId?: string
	frontendVersion?: string
	exportedAt: string
}

type LiveExportFailurePayload = {
	requestId: string
	ok: false
	error: {
		code: 'graph_to_prompt_failed' | 'invalid_export_shape'
		message: string
	}
	clientId?: string
	graphId?: string
	frontendVersion?: string
	exportedAt: string
}

type LiveExportPayload = LiveExportSuccessPayload | LiveExportFailurePayload

type LiveExportMetadata = {
	clientId?: string
	graphId?: string
	frontendVersion?: string
	workflowTitle?: string
	pageTitle?: string
}

type AppWithLiveExport = typeof app & {
	api?: {
		clientId?: string
	}
	graphToPrompt?: () => Promise<GraphToPromptResult>
}

declare global {
	interface WindowEventMap {
		'imagegen-toolkit.live-export.request': CustomEvent<LiveExportRequestDetail>
	}

	var graph:
		| {
			id?: string
			extra?: {
				frontendVersion?: string
			}
		}
		| undefined
}

const TARGET_NODE_NAME = 'load-video-url'
const PREVIEW_WIDGET_NAME = 'video_url_preview'
const MIN_NODE_WIDTH = 320
const DEFAULT_PREVIEW_ASPECT_RATIO = 16 / 9
const MIN_PREVIEW_HEIGHT = 120
const NODE_CHROME_HEIGHT = 120
const EXTENSION_NAME = 'imagegen-toolkit-dev-utils.load-video-url-preview'
const LIVE_EXPORT_EVENT = 'imagegen-toolkit.live-export.request'
const LIVE_EXPORT_RESULT_PATH = '/image-gen-toolkit/live-export/result'
const LIVE_EXPORT_EXTENSION_NAME = 'imagegen-toolkit-dev-utils.live-export-bridge'

let liveExportListenerRegistered = false

console.info(`[${EXTENSION_NAME}] build`, __IMAGEGEN_TOOLKIT_BUILD_INFO__)

function getLiveExportMetadata(): LiveExportMetadata {
	const liveExportApp = app as AppWithLiveExport
	const pageTitle = normalizeLiveExportPageTitle(document.title)

	return {
		clientId: liveExportApp.api?.clientId,
		graphId: globalThis.graph?.id,
		frontendVersion: globalThis.graph?.extra?.frontendVersion,
		workflowTitle: deriveLiveExportWorkflowTitle(pageTitle),
		pageTitle
	}
}

function normalizeLiveExportPageTitle(value: string | null | undefined): string | undefined {
	if (typeof value !== 'string') {
		return undefined
	}

	const normalized = value.replace(/\s+/g, ' ').trim()
	return normalized ? normalized : undefined
}

function sanitizeLiveWorkflowTitle(value: string): string | undefined {
	const normalized = value
		.replace(/^[*\u2022]\s*/, '')
		.replace(/\s+/g, ' ')
		.trim()

	if (!normalized || normalized.toLowerCase() === 'comfyui') {
		return undefined
	}

	return normalized
}

function deriveLiveExportWorkflowTitle(pageTitle: string | undefined): string | undefined {
	if (!pageTitle) {
		return undefined
	}

	const candidates = [
		pageTitle.replace(/\s*[-|]\s*ComfyUI$/i, ''),
		pageTitle.replace(/^ComfyUI\s*[-|]\s*/i, ''),
		pageTitle
	]

	for (const candidate of candidates) {
		const workflowTitle = sanitizeLiveWorkflowTitle(candidate)
		if (workflowTitle) {
			return workflowTitle
		}
	}

	return undefined
}

function getReadableErrorMessage(error: unknown): string {
	if (error instanceof Error && error.message.trim()) {
		return error.message
	}

	if (typeof error === 'string' && error.trim()) {
		return error
	}

	return 'Live export failed in the ComfyUI frontend runtime'
}

async function postLiveExportResult(payload: LiveExportPayload) {
	await api.fetchApi(LIVE_EXPORT_RESULT_PATH, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(payload)
	})
}

async function handleLiveExportRequest(event: CustomEvent<LiveExportRequestDetail>) {
	const requestId = event.detail?.requestId?.trim()
	if (!requestId) {
		return
	}

	const metadata = getLiveExportMetadata()
	const exportedAt = new Date().toISOString()
	const liveExportApp = app as AppWithLiveExport

	try {
		const graphToPrompt = liveExportApp.graphToPrompt
		if (typeof graphToPrompt !== 'function') {
			throw new Error('app.graphToPrompt is unavailable')
		}

		const { output } = await graphToPrompt.call(liveExportApp)
		if (!output || typeof output !== 'object' || Array.isArray(output)) {
			await postLiveExportResult({
				requestId,
				ok: false,
				error: {
					code: 'invalid_export_shape',
					message: 'app.graphToPrompt() returned an invalid apiPrompt payload'
				},
				...metadata,
				exportedAt
			})
			return
		}

		await postLiveExportResult({
			requestId,
			ok: true,
			apiPrompt: output,
			...metadata,
			exportedAt
		})
	} catch (error) {
		await postLiveExportResult({
			requestId,
			ok: false,
			error: {
				code: 'graph_to_prompt_failed',
				message: getReadableErrorMessage(error)
			},
			...metadata,
			exportedAt
		})
	}
}

function getVideoUrlWidget(node: NodeLike): WidgetLike | undefined {
	return node.widgets?.find((widget) => widget.name === 'video_url')
}

function getWidgetByName(node: NodeLike, widgetName: string): WidgetLike | undefined {
	return node.widgets?.find((widget) => widget.name === widgetName)
}

function isPreviewableMp4Url(value: unknown): value is string {
	if (typeof value !== 'string') {
		return false
	}

	const normalizedValue = value.trim()
	if (!normalizedValue) {
		return false
	}

	try {
		const parsed = new URL(normalizedValue)
		return (
			(parsed.protocol === 'http:' || parsed.protocol === 'https:') &&
			parsed.pathname.toLowerCase().endsWith('.mp4')
		)
	} catch {
		return false
	}
}

function getIntrinsicAspectRatio(video: HTMLVideoElement): number | null {
	if (video.videoWidth <= 0 || video.videoHeight <= 0) {
		return null
	}

	return video.videoWidth / video.videoHeight
}

function resizeNodeForPreview(node: NodeLike, aspectRatio = DEFAULT_PREVIEW_ASPECT_RATIO) {
	const computedSize = node.computeSize?.()
	if (!computedSize) {
		return
	}

	const nextWidth = Math.max(node.size?.[0] ?? computedSize[0], MIN_NODE_WIDTH)
	const previewWidth = Math.max(nextWidth - 16, MIN_NODE_WIDTH - 16)
	const previewHeight = Math.max(Math.round(previewWidth / aspectRatio), MIN_PREVIEW_HEIGHT)

	const nextSize: [number, number] = [
		nextWidth,
		Math.max(computedSize[1], previewHeight + NODE_CHROME_HEIGHT)
	]

	if (node.size?.[0] === nextSize[0] && node.size?.[1] === nextSize[1]) {
		return
	}

	if (typeof node.setSize === 'function') {
		node.setSize(nextSize)
		return
	}

	node.size = nextSize
}

function attachPreview(node: NodeLike) {
	if (node.__loadVideoUrlPreviewState || typeof node.addDOMWidget !== 'function') {
		return
	}

	const wrapper = document.createElement('div')
	wrapper.style.display = 'none'
	wrapper.style.width = '100%'
	wrapper.style.padding = '8px 0 0'
	wrapper.style.aspectRatio = `${DEFAULT_PREVIEW_ASPECT_RATIO}`

	const video = document.createElement('video')
	video.controls = true
	video.autoplay = true
	video.loop = true
	video.muted = true
	video.playsInline = true
	video.preload = 'metadata'
	video.style.width = '100%'
	video.style.height = '100%'
	video.style.display = 'block'
	video.style.objectFit = 'contain'
	video.style.background = '#111'
	video.style.borderRadius = '8px'

	wrapper.append(video)

	let previewAspectRatio = DEFAULT_PREVIEW_ASPECT_RATIO

	const applyPreviewAspectRatio = (nextAspectRatio: number | null) => {
		previewAspectRatio = nextAspectRatio && Number.isFinite(nextAspectRatio) && nextAspectRatio > 0
			? nextAspectRatio
			: DEFAULT_PREVIEW_ASPECT_RATIO
		wrapper.style.aspectRatio = `${previewAspectRatio}`
		resizeNodeForPreview(node, previewAspectRatio)
	}

	node.addDOMWidget(PREVIEW_WIDGET_NAME, 'preview', wrapper, {
		serialize: false,
		hideOnZoom: false,
		getValue() {
			return null
		},
		setValue() {
			return undefined
		}
	})

	const resizeObserver = new ResizeObserver(() => {
		if (wrapper.style.display !== 'none') {
			resizeNodeForPreview(node, previewAspectRatio)
		}
	})
	resizeObserver.observe(wrapper)

	video.addEventListener('loadedmetadata', () => {
		applyPreviewAspectRatio(getIntrinsicAspectRatio(video))
	})

	video.addEventListener('emptied', () => {
		applyPreviewAspectRatio(null)
	})

	const sync = () => {
		const widget = getVideoUrlWidget(node)
		const rawValue = typeof widget?.value === 'string' ? widget.value : ''
		const nextUrl = rawValue.trim()

		if (!isPreviewableMp4Url(nextUrl)) {
			wrapper.style.display = 'none'
			applyPreviewAspectRatio(null)
			video.pause()
			delete video.dataset.previewUrl
			video.removeAttribute('src')
			video.load()
			return
		}

		wrapper.style.display = 'block'
		if (video.dataset.previewUrl !== nextUrl) {
			applyPreviewAspectRatio(null)
			video.dataset.previewUrl = nextUrl
			video.src = nextUrl
			video.load()
		}

		void video.play().catch(() => undefined)
		resizeNodeForPreview(node, previewAspectRatio)
	}

	const cleanup = () => {
		resizeObserver.disconnect()
		video.pause()
		delete video.dataset.previewUrl
		video.removeAttribute('src')
		video.load()
	}

	const widget = getVideoUrlWidget(node)
	const originalCallback = widget?.callback
	if (widget) {
		widget.callback = function (...args: unknown[]) {
			const callbackResult = originalCallback?.apply(this, args)
			sync()
			return callbackResult
		}
	}

	const originalOnRemoved = node.onRemoved
	node.onRemoved = function (...args: unknown[]) {
		cleanup()
		return originalOnRemoved?.apply(this, args)
	}

	node.__loadVideoUrlPreviewState = {
		sync,
		cleanup
	}

	sync()
}

app.registerExtension({
	name: EXTENSION_NAME,
	beforeRegisterNodeDef(nodeType: NodeTypeLike, nodeData: NodeDefinitionLike) {
		if (nodeData.name === TARGET_NODE_NAME) {
			const originalOnNodeCreated = nodeType.prototype.onNodeCreated
			nodeType.prototype.onNodeCreated = function (...args: unknown[]) {
				const result = originalOnNodeCreated?.apply(this, args)
				attachPreview(this)
				return result
			}

			const originalOnConfigure = nodeType.prototype.onConfigure
			nodeType.prototype.onConfigure = function (...args: unknown[]) {
				const result = originalOnConfigure?.apply(this, args)
				attachPreview(this)
				this.__loadVideoUrlPreviewState?.sync()
				return result
			}
		}
	}
})

app.registerExtension({
	name: LIVE_EXPORT_EXTENSION_NAME,
	async setup() {
		if (liveExportListenerRegistered) {
			return
		}

		api.addEventListener(LIVE_EXPORT_EVENT, handleLiveExportRequest)
		liveExportListenerRegistered = true
	}
})