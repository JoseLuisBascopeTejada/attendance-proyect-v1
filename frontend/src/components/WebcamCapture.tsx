import { useCallback, useRef } from 'react';
import Webcam from 'react-webcam';

interface WebcamCaptureProps {
  onCapture: (imageSrc: string) => void;
  width?: number;
  height?: number;
}

export function WebcamCapture({ onCapture, width = 640, height = 480 }: WebcamCaptureProps) {
  const webcamRef = useRef<Webcam>(null);

  const capture = useCallback(() => {
    const imageSrc = webcamRef.current?.getScreenshot();
    if (imageSrc) {
      onCapture(imageSrc);
    }
  }, [onCapture]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
      <div
        style={{
          borderRadius: '12px',
          overflow: 'hidden',
          border: '2px solid var(--border)',
          lineHeight: 0,
        }}
      >
        <Webcam
          audio={false}
          ref={webcamRef}
          screenshotFormat="image/jpeg"
          width={width}
          height={height}
          videoConstraints={{ width, height, facingMode: 'user' }}
          style={{ transform: 'scaleX(-1)', width: '100%', height: 'auto' }}
        />
      </div>
      <button
        type="button"
        onClick={capture}
        style={{
          padding: '10px 24px',
          borderRadius: '8px',
          border: 'none',
          background: 'var(--accent)',
          color: '#fff',
          fontSize: '15px',
          fontWeight: 600,
          cursor: 'pointer',
          letterSpacing: '0.3px',
        }}
      >
        Capture Photo
      </button>
    </div>
  );
}
