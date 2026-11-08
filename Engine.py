from pydantic import BaseModel, Field
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
import httpx
import time


# 1. 공통 인터페이스

class ProtocolModule(ABC):
    """모든 통신 모듈(HTTP, TCP, DNS 등)이 상속받아야 하는 기본 뼈대"""
    @abstractmethod
    async def execute(self, request_data: Any) -> Any:
        pass
    
    @abstractmethod
    async def close(self):
        pass


# 2. HTTP 모듈

class RenderedHTTPRequest(BaseModel):
    method: str
    url: str
    headers: dict = Field(default_factory=dict)
    body: Optional[str] = None

class HTTPScannerResponse(BaseModel):
    status_code: int
    headers: dict
    body: str
    response_time_ms: float
    error_msg: Optional[str] = None

class HttpModule(ProtocolModule):
    """HTTP/HTTPS 통신을 담당하는 모듈"""
    def __init__(self, timeout: float = 10.0, max_connections: int = 50):
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=max_connections)
        self.client = httpx.AsyncClient(verify=False, follow_redirects=False, timeout=timeout, limits=limits)

    async def execute(self, request_data: RenderedHTTPRequest) -> HTTPScannerResponse:
        start_time = time.perf_counter()
        try:
            response = await self.client.request(
                method=request_data.method,
                url=request_data.url,
                headers=request_data.headers,
                content=request_data.body.encode('utf-8') if request_data.body else None
            )
            return HTTPScannerResponse(
                status_code=response.status_code,
                headers=dict(response.headers),
                body=response.text,
                response_time_ms=(time.perf_counter() - start_time) * 1000
            )
        except Exception as e:
            return HTTPScannerResponse(
                status_code=0, headers={}, body="", 
                response_time_ms=(time.perf_counter() - start_time) * 1000, error_msg=str(e)
            )

    async def close(self):
        await self.client.aclose()




# 3. 코어 스캐너 엔진 (모듈을 관리하는 본체)

class ScannerEngine:
    """여러 프로토콜 모듈을 장착하고 관리하는 메인 엔진"""
    def __init__(self):
        # 딕셔너리 형태로 모듈들을 슬롯에 장착하여 관리
        self.modules: Dict[str, ProtocolModule] = {}

    def register_module(self, protocol_name: str, module: ProtocolModule):
        self.modules[protocol_name] = module

    async def run_scan(self, protocol_name: str, request_data: Any) -> Any:
        if protocol_name not in self.modules:
            raise ValueError(f"존재하지 않는 모듈입니다: {protocol_name}")
        
        # 선택된 모듈에 스캔 작업을 위임
        return await self.modules[protocol_name].execute(request_data)

    async def shutdown(self):
        for name, module in self.modules.items():
            await module.close()
            print(f"[{name}] 모듈 종료 완료")


# 4. Lifespan

core_engine = ScannerEngine()

@asynccontextmanager
async def lifespan(app: FastAPI):
    http_module = HttpModule(timeout=10.0, max_connections=50)
    core_engine.register_module("http", http_module)
    
    
    yield
    
    await core_engine.shutdown()
    print("스캐너 코어 엔진 종료")

app = FastAPI(lifespan=lifespan)

def get_engine() -> ScannerEngine:
    return core_engine

@app.post("/scan/http")
async def execute_http_scan(request: RenderedHTTPRequest, engine: ScannerEngine = Depends(get_engine)):
    result = await engine.run_scan("http", request)
    return {"protocol": "http", "result": result}