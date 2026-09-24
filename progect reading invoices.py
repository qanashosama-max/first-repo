
import base64 
import json                                                                                                     
import os
import tkinter as tk
from tkinter import filedialog
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class InvoiceItem:
    name: str
    quantity: float
    unit_price: float
    total_price: float

@dataclass
class InvoiceData:
    company_name: Optional[str]
    invoice_date: Optional[str]
    items: list[InvoiceItem] = field(default_factory=list)
    payment_method: Optional[str] = None # "cash" | "credit" | "transfer"
    total_amount: Optional[float] = None
    raw_response: Optional[str] = None # نص خام لو صار خطأ بالتحويل

 
class InvoiceReader:

    SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".webp"}

    def __init__(self, api _key: Optional[str] = None, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self.model = model

    def _encode_image(self, image_path: str) -> tuple[str, str]:
        path = Path(image_path)                                                                                                   
        if not path.exists():
            raise FileNotFoundError(f"الصورة غير موجودة: {image_path}")
        if path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(f"صيغة غير مدعومة: {path.suffix}")

        media_type = f"image/{path.suffix.lower().lstrip('.')}"
        media_type = media_type.replace("jpg", "jpeg")

        with open(path, "rb") as f:
            encoded = base64.standard_b64encode(f.read()).decode("utf-8")

        return encoded, media_type

    def _build_prompt(self) -> str:
        return """
أنت خبير في قراءة الفواتير. استخرج المعلومات التالية من الفاتورة في الصورة المرفقة،
وأعد الإجابة بصيغة JSON فقط، بدون أي نص إضافي أو شرح، وبالشكل التالي بالضبط:

{
  "company_name": "اسم الشركة أو صاحب الفاتورة",
  "invoice_date": "التاريخ كما هو مكتوب بالفاتورة",
  "items": [
    {"name": "اسم السلعة", "quantity": 0, "unit_price": 0, "total_price": 0}
  ],
  "payment_method": "cash او credit او transfer",
  "total_amount": 0
}

ملاحظات:
- إذا لم تجد معلومة معينة، ضع null بدلاً منها.
- الأرقام يجب أن تكون أرقام فعلية (numbers) وليست نصوص.
- لا تكتب أي شيء خارج الـ JSON.
""".strip()

    def read_invoice(self, image_path: str) -> InvoiceData:
        encoded_image, media_type = self._encode_image(image_path)

        message = self.client.messages.create(
            model=self.model,
            max_tokens=1500,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": encoded_image,
                            },
                        },
                        {"type": "text", "text": self._build_prompt()},
                    ],
                }
            ],
        )
                                     
        raw_text = message.content[0].text.strip()
        cleaned = raw_text.replace("```json", "").replace("```", "").strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return InvoiceData(company_name=None, invoice_date=None, raw_response=raw_text)
                                                                              
        items = [
            InvoiceItem(
                name=item.get("name") or "not defined",
                quantity=item.get("quantity") or 0,
                unit_price=item.get("unit_price") or 0,
                total_price=item.get("total_price") or 0,
            )
            for item in data.get("items", [])
        ]
        
        return InvoiceData(
            company_name=data.get("company_name"),
            invoice_date=data.get("invoice_date"),
            items=items,
            payment_method=data.get("payment_method"),
            total_amount=data.get("total_amount"),
        )


def choose_image() -> str:

    root = tk.Tk()
    root.withdraw() 

    file_path = filedialog.askopenfilename(
        title="اختر صورة الفاتورة",
        filetypes=[("Image files", "*.jpg *.jpeg *.png *.webp")],
    )
    root.destroy()
    return file_path


def print_invoice(invoice: InvoiceData) -> None:
    if invoice.raw_response:
        print(" لم يتم تحليل الفاتورة بشكل صحيح، الرد الخام:")
        print(invoice.raw_response)
        return
                               
    print("=" * 40)
    print(f"اسم الشركة / صاحب الفاتورة : {invoice.company_name}")
    print(f"التاريخ : {invoice.invoice_date}")
    print(f"طريقة الدفع : {invoice.payment_method}")
    print("-" * 40)
    print("السلع:")
    for item in invoice.items:
        print(f" - {item.name} | الكمية: {item.quantity} | "
              f"سعر الوحدة: {item.unit_price} | الإجمالي: {item.total_price}")
    print("-" * 40)
    print(f"عدد السلع : {len(invoice.items)}")
    print(f"التوتال الكامل : {invoice.total_amount}")
    print("=" * 40)
                
                                                                                                             
if __name__ == "__main__":
    reader = InvoiceReader()  

    print(" افتح نافذة اختيار الصورة...") 
    image_path = choose_image()

    if not image_path:
        print(" لم يتم اختيار أي صورة.")
    else:
        try:
            invoice = reader.read_invoice(image_path)
            print_invoice(invoice)
        except (FileNotFoundError, ValueError) as e:
            print(f" خطأ: {e}")




