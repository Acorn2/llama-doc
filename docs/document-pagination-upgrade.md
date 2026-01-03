# 文档分页接口优化说明

## 问题描述

原有的 `GET /api/v1/documents` 接口返回格式如下：

```json
[
  {
    "document_id": "b95c392c-c50a-44e1-9977-e4aca6f40ea6",
    "filename": "我 在 苏 联 当 翻 译【硬核狠人86】.txt",
    "file_size": 36862,
    "file_md5": "d318ab6d7845356a41412237277f4381",
    "pages": 1,
    "upload_time": "2025-07-29T20:26:28.599318+08:00",
    "status": "completed",
    "file_type": "txt",
    "chunk_count": 15,
    "retry_count": 0,
    "max_retries": 3
  }
]
```

**存在的问题：**
- 无法获取数据总条数
- 无法获取总页数
- 无法判断是否支持翻页
- 前端无法实现完整的分页功能

## 解决方案

### 1. 新增响应模型

在 `app/schemas.py` 中新增 `DocumentListResponse` 模型：

```python
class DocumentListResponse(BaseModel):
    """文档列表响应模型"""
    items: List[DocumentInfo] = Field(..., description="文档列表")
    total: int = Field(..., description="文档总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    total_pages: int = Field(..., description="总页数")
    has_next: bool = Field(..., description="是否有下一页")
    has_prev: bool = Field(..., description="是否有上一页")
```

### 2. 更新接口实现

修改 `list_documents` 函数，增加分页信息计算：

```python
@router.get("", response_model=DocumentListResponse)
async def list_documents(
    skip: int = 0, 
    limit: int = 20, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 获取总数
    total = db.query(Document).filter(
        Document.user_id == current_user.id
    ).count()
    
    # 获取分页数据
    documents = db.query(Document).filter(
        Document.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    
    # 计算分页信息
    page = (skip // limit) + 1 if limit > 0 else 1
    total_pages = (total + limit - 1) // limit if limit > 0 else 1
    has_next = skip + limit < total
    has_prev = skip > 0
    
    # 返回完整的分页响应
    return DocumentListResponse(
        items=document_items,
        total=total,
        page=page,
        page_size=limit,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev
    )
```

## 优化后的返回格式

```json
{
  "items": [
    {
      "document_id": "b95c392c-c50a-44e1-9977-e4aca6f40ea6",
      "filename": "我 在 苏 联 当 翻 译【硬核狠人86】.txt",
      "file_size": 36862,
      "file_md5": "d318ab6d7845356a41412237277f4381",
      "pages": 1,
      "upload_time": "2025-07-29T20:26:28.599318+08:00",
      "status": "completed",
      "file_type": "txt",
      "chunk_count": 15,
      "retry_count": 0,
      "max_retries": 3
    }
  ],
  "total": 25,
  "page": 1,
  "page_size": 10,
  "total_pages": 3,
  "has_next": true,
  "has_prev": false
}
```

## 受影响的接口

以下接口已更新为新的分页格式：

1. `GET /api/v1/documents` - 获取用户文档列表
2. `GET /api/v1/llamaindex/documents` - 获取LlamaIndex文档列表

## 前端使用示例

```javascript
// 获取文档列表
const response = await fetch('/api/v1/documents?skip=0&limit=10');
const data = await response.json();

// 现在可以获取完整的分页信息
console.log('总文档数:', data.total);
console.log('当前页:', data.page);
console.log('总页数:', data.total_pages);
console.log('是否有下一页:', data.has_next);
console.log('是否有上一页:', data.has_prev);
console.log('文档列表:', data.items);

// 实现分页导航
if (data.has_next) {
  // 显示下一页按钮
}
if (data.has_prev) {
  // 显示上一页按钮
}
```

## 优势

1. **完整的分页信息**：提供总数、页码、是否有更多页等信息
2. **前端友好**：前端可以轻松实现分页组件
3. **向后兼容**：文档数据结构保持不变，只是包装在新的响应格式中
4. **统一性**：与其他分页接口保持一致的响应格式
5. **可扩展性**：未来可以轻松添加更多分页相关的元数据