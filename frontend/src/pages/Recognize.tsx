import { useState } from 'react';
import { apiClient } from '../api/client';
import { WebcamCapture } from '../components/WebcamCapture';

function base64ToBlob(base64: string): Blob {
  const [header, data] = base64.split(',');
  const mime = header.match(/:(.*?);/)?.[1] ?? 'image/jpeg';
  const binary = atob(data);
  const array = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    array[i] = binary.charCodeAt(i);
  }
  return new Blob([array], { type: mime });
}

interface MatchResult {
  name: string;
  distance: number;
  studentId: number;
  duplicate?: boolean;
}

export function Recognize() {
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<MatchResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleCapture = async (imageSrc: string) => {
    setCapturedImage(imageSrc);
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const blob = base64ToBlob(imageSrc);
      const formData = new FormData();
      formData.append('file', blob, 'photo.jpg');

      const response = await apiClient.post('/recognize', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setResult({
        name: response.data.name,
        distance: response.data.distance,
        studentId: response.data.student_id,
        duplicate: response.data.duplicate,
      });
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

        if (status === 404) {
          setError(detail ?? 'Rostro no reconocido. Registre este estudiante primero.');
        } else if (status === 413) {
          setError(detail ?? 'Imagen demasiado grande o con dimensiones excesivas.');
        } else if (status === 400) {
          setError(detail ?? 'Rostro demasiado pequeño. Acérquese a la cámara.');
        } else {
          setError(detail ?? 'Error al reconocer. Intente de nuevo.');
        }
      } else {
        setError('Error de red. ¿Está el backend ejecutándose?');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 700, margin: '0 auto', padding: '32px 20px' }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8, color: 'var(--text-h)' }}>
        Reconocimiento Facial
      </h1>
      <p style={{ color: 'var(--text)', marginBottom: 24 }}>
        Capture una foto para identificar al estudiante.
      </p>

      <div style={{ marginBottom: 24 }}>
        <WebcamCapture onCapture={handleCapture} />
      </div>

      {capturedImage && (
        <div style={{ marginBottom: 20, textAlign: 'center' }}>
          <p style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: 'var(--text-h)' }}>
            Foto capturada
          </p>
          <img
            src={capturedImage}
            alt="Captured"
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
          <span style={{ marginLeft: 8 }}>Analizando...</span>
        </div>
      )}

      {result && (
        <div
          style={{
            marginTop: 16,
            padding: '16px 20px',
            borderRadius: 8,
            background: 'var(--accent-bg)',
            border: '1px solid var(--accent)',
          }}
        >
          <p style={{ fontSize: 22, fontWeight: 700, margin: '0 0 4px', color: 'var(--text-h)' }}>
            {result.name}
          </p>
          <p style={{ fontSize: 13, margin: 0, color: 'var(--text)' }}>
            Distancia: {result.distance.toFixed(4)}
          </p>
          <p style={{ fontSize: 13, margin: '4px 0 0', color: 'var(--text)' }}>
            ID: {result.studentId}
          </p>
          {result.duplicate && (
            <p style={{ fontSize: 13, margin: '8px 0 0', color: 'var(--accent)', fontWeight: 600 }}>
              Asistencia ya registrada recientemente
            </p>
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
