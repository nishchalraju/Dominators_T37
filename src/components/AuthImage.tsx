import { ImageOff } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '@/services/api'
import { isAbort } from '@/utils/errors'
import { Skeleton } from './ui/Feedback'

interface Props {
  /** Relative API URL, for example /api/sketch-versions/3/image */
  src: string
  alt: string
  className?: string
}

/**
 * Sketch images need the Authorization header, which a plain <img src> cannot send. So the image is
 * fetched as a blob and shown from an object URL (released again when the component goes away).
 */
export function AuthImage(props: Props) {
  // keyed by the URL: a different image starts from a clean loading state
  return <LoadedImage key={props.src} {...props} />
}

function LoadedImage({ src, alt, className = '' }: Props) {
  const [state, setState] = useState<{ url?: string; failed?: boolean }>({})

  useEffect(() => {
    const controller = new AbortController()
    let objectUrl: string | undefined
    api
      .imageBlob(src, { signal: controller.signal })
      .then(({ blob }) => {
        if (controller.signal.aborted) return
        objectUrl = URL.createObjectURL(blob)
        setState({ url: objectUrl })
      })
      .catch((error: unknown) => {
        if (!isAbort(error)) setState({ failed: true })
      })
    return () => {
      controller.abort()
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [src])

  if (state.failed) {
    return (
      <div role="img" aria-label={`${alt} (could not be loaded)`} className={`flex flex-col items-center justify-center gap-2 bg-raised text-sm text-muted ${className}`}>
        <ImageOff className="size-6" aria-hidden="true" />
        Image unavailable
      </div>
    )
  }
  if (!state.url) return <Skeleton className={className} />
  return <img src={state.url} alt={alt} className={className} draggable={false} />
}
