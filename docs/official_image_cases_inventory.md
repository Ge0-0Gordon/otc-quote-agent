# Official Embedded-Image Case Inventory

Source: `金融创新业务部衍生品参考资料.docx`, section `4）相关询价案例`.

## Inspection result

The document contains six inline images, corresponding one-to-one with cases
1-6. Cases 7-13 are native document text. The six images were inspected at
their original resolution and manually transcribed into
`reference_materials/inquiry_cases.yaml` and
`sample_data/reference_case_0*_*.txt`.

| Case | DOCX image | Visible structure | Current handling |
|---|---|---|---|
| 1 | `word/media/image1.png` | European snowball matrix | Snowball, partial, multiple alternatives |
| 2 | `word/media/image2.png` | Large snowball, terminal knock-in observation | Snowball, partial |
| 3 | `word/media/image3.png` | Snowball matrix | Snowball, partial, multiple alternatives |
| 4 | `word/media/image4.jpeg` | Classic snowball matrix | Snowball, partial, multiple alternatives |
| 5 | `word/media/image5.png` | Classic snowball matrix | Snowball, partial, multiple alternatives |
| 6 | `word/media/image6.png` | Phoenix and terminal-observation DCN | Unsupported |

## Verification boundary

- The transcription preserves visible terms and marks unresolved coupon values
  as pending rather than inventing them.
- Images 1-5 contain several rows or alternative parameter combinations. They
  should eventually use `quote_candidates`; they must not be merged into one
  synthetic quote.
- Image 6 explicitly contains Phoenix and DCN. It remains unsupported and must
  not enter a Snowball, FCN, or European Option schema.
- The original image binaries are not copied into the repository.

## OCR decision

Runtime OCR is not added in this version. The local environment did not expose
a reliable OCR engine, and the source images contain dense tables where OCR
errors could silently change barriers, coupons, or notionals. The current
scanned-PDF behavior therefore remains an explicit unsupported error.

OCR should be reconsidered only if scanned documents are a demonstrated input
requirement. At that point it should be an optional parser with field-level
confidence, source coordinates, manual review thresholds, and a golden
evaluation set. It must not silently fall back or overwrite text extraction.
