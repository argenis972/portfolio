/**
 * useContactForm — encapsulates state and submission logic for the Contact form.
 */
import { useState } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { useContactMutation } from './useApi';
import { ApiError } from '../api/client';

export function useContactForm() {
  const { t } = useLanguage();
  const { mutate, isPending: isMutating, isSuccess: mutationSuccess, error: mutationError, reset } = useContactMutation();

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    subject: '',
    message: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [traceResult, setTraceResult] = useState<{ traceId?: string; durationMs: number; queueStatus?: string; deliveryMode?: string; downstream?: string; message?: string } | null>(null);

  const getNewKey = () => {
    return typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `key-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
  };

  const [idempotencyKey, setIdempotencyKey] = useState<string>(getNewKey);

  const generateNewKey = () => {
    setIdempotencyKey(getNewKey());
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.name.trim()) newErrors.name = 'name_required';
    if (!formData.email.trim()) {
      newErrors.email = 'email_required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'email_invalid';
    }
    if (!formData.message.trim()) {
      newErrors.message = 'message_required';
    } else if (formData.message.length < 10) {
      newErrors.message = 'message_too_short';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    setErrors({});

    const dataToSend = {
      ...formData,
      subject: formData.subject.trim() || t('contact.subject_default') || 'Contact via Portfolio',
      website: (document.getElementById('hp_website') as HTMLInputElement)?.value || '',
      fax: (document.getElementById('hp_fax') as HTMLInputElement)?.value || ''
    };

    mutate(
      { data: dataToSend, idempotencyKey },
      {
        onSuccess: (result) => {
          setTraceResult(result);
          setFormData({ name: '', email: '', subject: '', message: '' });
          generateNewKey();
        },
        onError: (error: unknown) => {
          if (error instanceof ApiError) {
            if (error.status === 429) {
              setErrors({ submit: 'contact.error.rate_limit' });
            } else if (error.message.includes('DUPLICATE') || error.status === 409 || error.status === 400) {
              setErrors({ submit: 'contact.error.duplicate' });
            } else {
              setErrors({ submit: 'contact.error.generic' });
            }
          } else {
            setErrors({ submit: 'contact.error.generic' });
          }
          generateNewKey();
        }
      }
    );
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));

    if (mutationSuccess || mutationError || errors.submit) {
      reset();
    }

    if (errors[name]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  const status = isMutating ? 'loading' : (mutationSuccess ? 'success' : (mutationError || errors.submit ? 'error' : 'idle'));
  const submitError = errors.submit ? t(errors.submit) : t('contact.error.generic');
  const responseStatusCode = mutationError instanceof ApiError ? mutationError.status : null;
  const responseTraceId = traceResult?.traceId || (mutationError instanceof ApiError ? mutationError.traceId : undefined);
  const queueStatus = traceResult?.queueStatus ?? 'idle';
  const deliveryMode = traceResult?.deliveryMode ?? 'background';
  const downstream = traceResult?.downstream ?? 'email_adapter';
  const responseTone = status === 'success'
    ? 'text-emerald-400'
    : status === 'error'
      ? 'text-red-400'
      : status === 'loading'
        ? 'text-amber-400'
        : 'text-slate-400';

  return {
    formData,
    errors,
    traceResult,
    idempotencyKey,
    status,
    submitError,
    responseStatusCode,
    responseTraceId,
    queueStatus,
    deliveryMode,
    downstream,
    responseTone,
    handleChange,
    handleSubmit
  };
}
