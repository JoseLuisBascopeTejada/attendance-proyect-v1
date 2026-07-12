import { useRef, useState, useCallback } from 'react';
import Webcam from 'react-webcam';
import { apiClient } from '../api/client';

interface MatchEntry {
  name: string;
  distance: number;
  bbox: number[];
  duplicate?: boolean;
}

function resizeImage(base64: string, maxWidth = 800): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      const ratio = maxWidth / img.width;
      canvas.width = maxWidth;
      canvas.height = img.height * ratio;
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        reject(new Error('Canvas context not available'));
        return;
      }
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(
        (blob) => {
          if (blob) resolve(blob);
          else reject(new Error('Failed to create blob'));
        },
        'image/jpeg',
        0.85,
      );
    };
    img.onerror = () => reject(new Error('Failed to load image'));
    img.src = base64;
  });
}

export function RecognizeGroup() {
  const webcamRef = useRef<Webcam>(null);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [matches, setMatches] = useState<MatchEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleCapture = useCallback(async () => {
    const imageSrc = webcamRef.current?.getScreenshot();
    if (!imageSrc) return;

    setCapturedImage(imageSrc);
    setLoading(true);
    setError(null);
    setMatches(null);

    try {
      const blob = await resizeImage(imageSrc);
      const formData = new FormData();
      formData.append('file', blob, 'photo.jpg');

      const response = await apiClient.post('/recognize-group', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setMatches(response.data.matches);
    } catch (err: unknown) {
      if (
        err &&
        typeof err === 'object' &&
        'response' in err &&
        err.response &&
        typeof err.response === 'object' &&
        'status' in err.response
      ) {
        const status = err.response.status as number;
        const detail = (err.response as { data?: { detail?: string } }).data?.detail;

        if (status === 413) {
          setError(detail ?? 'Imagen demasiado grande o con dimensiones excesivas.');
        } else {
          setError(detail ?? 'Error al procesar la foto grupal. Intente de nuevo.');
        }
      } else {
        setError('Error de red. ¿Está el backend ejecutándose?');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div style={{ maxWidth: 700, margin: '0 auto', padding: '32px 20px' }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8, color: 'var(--text-h)' }}>
        Reconocimiento Grupal
      </h1>
      <p style={{ color: 'var(--text)', marginBottom: 24 }}>
        Capture una foto grupal para identificar a todos los presentes.
      </p>

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
            width={640}
            height={480}
            videoConstraints={{ width: 640, height: 480, facingMode: 'user' }}
            style={{ transform: 'scaleX(-1)', width: '100%', height: 'auto' }}
          />
        </div>
        <button
          type="button"
          onClick={handleCapture}
          disabled={loading}
          style={{
            padding: '10px 24px',
            borderRadius: '8px',
            border: 'none',
            background: loading ? '#999' : 'var(--accent)',
            color: '#fff',
            fontSize: '15px',
            fontWeight: 600,
            cursor: loading ? 'not-allowed' : 'pointer',
            letterSpacing: '0.3px',
          }}
        >
          {loading ? 'Analizando...' : 'Tomar foto grupal'}
        </button>
      </div>

      {capturedImage && (
        <div style={{ marginTop: 20, textAlign: 'center' }}>
          <p style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: 'var(--text-h)' }}>
            Foto capturada
          </p>
          <img
            src={capturedImage}
            alt="Captured group"
            style={{
              maxWidth: 320,
              borderRadius: 8,
              border: '1px solid var(--border)',
            }}
          />
        </div>
      )}

      {loading && (
        <div style={{ textAlign: 'center', marginTop: 16, color: 'var(--text)' }}>
          <div
            style={{
              display: 'inline-block',
              width: 24,
              height: 24,
              border: '3px solid var(--border)',
              borderTopColor: 'var(--accent)',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite',
            }}
          />
          <span style={{ marginLeft: 8 }}>Procesando foto grupal...</span>
        </div>
      )}

      {matches !== null && (
        <div style={{ marginTop: 16 }}>
          <p
            style={{
              fontSize: 16,
              fontWeight: 700,
              marginBottom: 12,
              color: 'var(--text-h)',
            }}
          >
            {matches.length} persona{matches.length !== 1 ? 's' : ''} reconocida
            {matches.length !== 1 ? 's' : ''}
          </p>

          {matches.length === 0 ? (
            <p style={{ color: 'var(--text)', fontSize: 14 }}>
              No se reconoció ningún rostro. Registre los estudiantes primero.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {matches.map((m, i) => (
                <div
                  key={i}
                  style={{
                    padding: '12px 16px',
                    borderRadius: 8,
                    background: 'var(--accent-bg)',
                    border: '1px solid var(--accent)',
                  }}
                >
                  <p style={{ fontSize: 18, fontWeight: 700, margin: 0, color: 'var(--text-h)' }}>
                    {m.name}
                  </p>
                  <p style={{ fontSize: 13, margin: '4px 0 0', color: 'var(--text)' }}>
                    Distancia: {m.distance.toFixed(4)}
                  </p>
                  {m.duplicate && (
                    <p style={{ fontSize: 13, margin: '4px 0 0', color: 'var(--accent)', fontWeight: 600 }}>
                      Asistencia ya registrada
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {error && (
        <div
          style={{
            marginTop: 16,
            padding: '12px 16px',
            borderRadius: 8,
            background: '#f8d7da',
            border: '1px solid #dc3545',
            color: '#721c24',
          }}
        >
          {error}
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
