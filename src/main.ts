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
	addDOMWidget?: (
		name: string,
		type: string,
		element: HTMLElement,
		options?: Record<string, unknown>
	) => DOMWidgetLike
	computeSize?: () => [number, number]
	setSize?: (size: [number, number]) => void
	onRemoved?: (...args: unknown[]) => unknown
	__loadVideoUrlPreviewState?: LoadVideoPreviewState
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
	beforeRegisterNodeDef?: (nodeType: NodeTypeLike, nodeData: NodeDefinitionLike) => void
}

const TARGET_NODE_NAME = 'load-video-url'
const PREVIEW_WIDGET_NAME = 'video_url_preview'
const MIN_NODE_WIDTH = 320
const DEFAULT_PREVIEW_ASPECT_RATIO = 16 / 9
const MIN_PREVIEW_HEIGHT = 120
const NODE_CHROME_HEIGHT = 120
const EXTENSION_NAME = 'imagegen-toolkit-dev-utils.load-video-url-preview'

console.info(`[${EXTENSION_NAME}] build`, __IMAGEGEN_TOOLKIT_BUILD_INFO__)

function getVideoUrlWidget(node: NodeLike): WidgetLike | undefined {
	return node.widgets?.find((widget) => widget.name === 'video_url')
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
	beforeRegisterNodeDef(nodeType, nodeData) {
		if (nodeData.name !== TARGET_NODE_NAME) {
			return
		}

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
})