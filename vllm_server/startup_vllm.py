#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.engine.async_llm_engine import AsyncLLMEngine
from vllm.entrypoints.openai.api_server import OpenAIAPIServer
from vllm.utils import random

def main():
    parser = argparse.ArgumentParser(description='Запуск vLLM сервера для генерации alt-текстов')
    parser.add_argument('--model', type=str, default='google/gemma-3-4b-it',
                      help='Путь или название модели')
    parser.add_argument('--dtype', type=str, default='bfloat16',
                      choices=['float16', 'bfloat16', 'float32'],
                      help='Тип данных для вычислений')
    parser.add_argument('--port', type=int, default=8000,
                      help='Порт для API сервера')
    parser.add_argument('--gpu-memory', type=float, default=0.9,
                      help='Доля GPU памяти для использования (0-1)')
    parser.add_argument('--host', type=str, default='localhost',
                      help='Хост для API сервера')
    args = parser.parse_args()

    # Настраиваем аргументы для движка vLLM
    engine_args = AsyncEngineArgs(
        model=args.model,
        dtype=args.dtype,
        max_model_len=2048,  # Максимальная длина последовательности
        gpu_memory_utilization=args.gpu_memory,
        tensor_parallel_size=1,  # Используем один GPU
        disable_log_stats=True,  # Отключаем лишние логи
        trust_remote_code=True,  # Необходимо для некоторых моделей
    )

    # Инициализируем движок
    engine = AsyncLLMEngine.from_engine_args(engine_args)

    # Запускаем OpenAI-совместимый API сервер
    server = OpenAIAPIServer(
        engine=engine,
        host=args.host,
        port=args.port,
        chat_template=True,  # Включаем поддержку чат-шаблонов
    )

    # Запускаем сервер
    server.run()

if __name__ == "__main__":
    main() 