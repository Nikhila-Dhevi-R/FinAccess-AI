import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { useSpeech } from './useSpeech';

let recognitionInstances;
let utterances;

class MockRecognition {
  constructor() {
    this.start = vi.fn();
    this.stop = vi.fn();
    this.abort = vi.fn();
    recognitionInstances.push(this);
  }
}

class MockUtterance {
  constructor(text) {
    this.text = text;
    utterances.push(this);
  }
}

function resultEvent(text) {
  return { results: [[{ transcript: text }]] };
}

beforeEach(() => {
  recognitionInstances = [];
  utterances = [];
  window.SpeechRecognition = MockRecognition;
  window.SpeechSynthesisUtterance = MockUtterance;
  globalThis.SpeechSynthesisUtterance = MockUtterance;
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: {
      getUserMedia: vi.fn().mockResolvedValue({
        getTracks: () => [{ stop: vi.fn() }],
      }),
    },
  });
  Object.defineProperty(window, 'speechSynthesis', {
    configurable: true,
    value: {
      cancel: vi.fn(),
      speak: vi.fn(),
      getVoices: vi.fn().mockReturnValue([]),
      onvoiceschanged: null,
    },
  });
});

describe('useSpeech', () => {
  test('resolves one recognition interaction exactly once when stop and onend overlap', async () => {
    const { result } = renderHook(() => useSpeech('en'));
    let completionCount = 0;
    let promise;

    await act(async () => {
      promise = result.current.listen().then((value) => {
        completionCount += 1;
        return value;
      });
      await Promise.resolve();
    });

    const recognition = recognitionInstances[0];
    act(() => recognition.onresult(resultEvent('hello')));
    act(() => result.current.stopListening());
    expect(recognition.stop).toHaveBeenCalledTimes(1);

    await act(async () => {
      recognition.onend();
      recognition.onend();
      await expect(promise).resolves.toBe('hello');
    });

    expect(completionCount).toBe(1);
  });

  test('surfaces microphone permission denial without creating a recognizer', async () => {
    navigator.mediaDevices.getUserMedia.mockRejectedValueOnce(
      Object.assign(new Error('denied'), { name: 'NotAllowedError' }),
    );
    const { result } = renderHook(() => useSpeech('en'));

    await act(async () => {
      await expect(result.current.listen()).resolves.toBe('');
    });

    expect(recognitionInstances).toHaveLength(0);
    expect(result.current.error).toMatch(/permission blocked/i);
  });

  test('reports unsupported recognition immediately', async () => {
    delete window.SpeechRecognition;
    const { result } = renderHook(() => useSpeech('en'));

    await act(async () => {
      await expect(result.current.listen()).resolves.toBe('');
    });

    expect(result.current.error).toMatch(/not supported/i);
  });

  test('aborts active recognition and resolves the pending interaction on unmount', async () => {
    const { result, unmount } = renderHook(() => useSpeech('hi'));
    let promise;
    await act(async () => {
      promise = result.current.listen();
      await Promise.resolve();
    });
    const recognition = recognitionInstances[0];
    act(() => recognition.onresult(resultEvent('नमस्ते')));

    unmount();

    expect(recognition.abort).toHaveBeenCalledTimes(1);
    await expect(promise).resolves.toBe('नमस्ते');
    expect(window.speechSynthesis.cancel).toHaveBeenCalled();
  });

  test('ignores synthesis completion callbacks after unmount', () => {
    const onEnd = vi.fn();
    const { result, unmount } = renderHook(() => useSpeech('ta'));

    act(() => result.current.speak('வணக்கம்', onEnd));
    const utterance = utterances[0];
    unmount();
    act(() => utterance.onend());

    expect(onEnd).not.toHaveBeenCalled();
  });

  test('cancels speech synthesis before starting recognition', async () => {
    const { result } = renderHook(() => useSpeech('en'));

    await act(async () => {
      result.current.listen();
      await Promise.resolve();
    });

    expect(window.speechSynthesis.cancel).toHaveBeenCalled();
    act(() => recognitionInstances[0].onend());
  });
});
