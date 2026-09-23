import os
import io
import shutil
import zipfile
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from loguru import logger

from app.domain.models.teaching_unit import TeachingUnit
from app.domain.models.slide import Slide
from app.domain.models.narration_segment import NarrationSegment
from app.infrastructure.presentation.slide_builder import SlideBuilder


def hex_to_rgb_tuple(hex_str: str, default: tuple[int, int, int] = (255, 255, 255)) -> tuple[int, int, int]:
    """Converts a hex color string to RGB tuple."""
    if not hex_str:
        return default
    hex_str = hex_str.strip().lstrip('#')
    if len(hex_str) == 3:
        hex_str = ''.join([c * 2 for c in hex_str])
    if len(hex_str) != 6:
        return default
    try:
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        return default


def hex_to_clean_hex(hex_str: str, default: str = "FFFFFF") -> str:
    """Returns 6-char uppercase hex string."""
    if not hex_str:
        return default
    clean = hex_str.strip().lstrip('#').upper()
    if len(clean) == 3:
        clean = ''.join([c * 2 for c in clean])
    if len(clean) == 6:
        return clean
    return default


def sanitize_title(title: str, max_words: int = 7) -> str:
    """Ensures slide titles are punchy, readable, and never collide with content."""
    if not title:
        return "Lesson Overview"
    title = title.replace("\n", " ").strip()
    if " - " in title:
        parts = title.split(" - ")
        title = parts[-1].strip()
    elif ": " in title:
        parts = title.split(": ")
        title = parts[-1].strip()
    elif " & " in title and len(title) > 45:
        parts = title.split(" & ")
        title = parts[0].strip()
        
    words = title.split()
    if len(words) > max_words:
        title = " ".join(words[:max_words])
    return title


class PureXmlPptxBuilder:
    """
    Template-cloning Pure Python OpenXML Presentation builder.
    Preserves 100% of official Mintbook graphics, logos, circles, and branding.
    100% resilient against WDAC/AppLocker DLL policies since it requires zero C-extensions.
    """
    @staticmethod
    def build_pptx(
        units: list[TeachingUnit],
        narration_map: dict,
        output_path: str,
        template_path: str | None = None,
        title_hex: str = "FFFFFF",
        body_hex: str = "E2E8F0",
        accent_hex: str = "14B8A6",
        bg_hex: str = "0B3436"
    ) -> list[Slide]:
        builder = SlideBuilder()
        slides = []
        
        # Locate official template
        if not template_path or not os.path.exists(template_path):
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            default_tpl = project_root / "template" / "template.pptx"
            if default_tpl.exists():
                template_path = str(default_tpl)

        has_template = template_path and os.path.exists(template_path)
        
        for idx, unit in enumerate(units):
            narration_text = narration_map.get(unit.unit_id, f"Overview of {unit.learning_goal}")
            slide_model = builder.build(unit, narration_text)
            slide_model.title = sanitize_title(slide_model.title)
            slides.append(slide_model)
            
        num_slides = len(slides)
        
        if has_template:
            try:
                with zipfile.ZipFile(template_path, 'r') as src_zip:
                    template_files = {name: src_zip.read(name) for name in src_zip.namelist()}
                    
                slide1_xml_str = template_files.get('ppt/slides/slide1.xml', b'').decode('utf-8')
                slide1_rels_str = template_files.get('ppt/slides/_rels/slide1.xml.rels', b'').decode('utf-8')
                
                with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
                    # Write static template files
                    for fname, data in template_files.items():
                        if (fname.startswith('ppt/slides/slide') or 
                            fname.startswith('ppt/slides/_rels/slide') or 
                            fname in ('[Content_Types].xml', 'ppt/presentation.xml', 'ppt/_rels/presentation.xml.rels', '_rels/.rels')):
                            continue
                        zip_out.writestr(fname, data)
                        
                    # Generate cloned slides
                    for idx, slide_model in enumerate(slides):
                        escaped_title = slide_model.title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
                        seq_str = f"{idx + 1:02d}"
                        
                        bullet_xml_parts = []
                        for b in slide_model.bullets:
                            escaped_b = b.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
                            bullet_xml_parts.append(f"""<a:p>
                                <a:pPr marL="285750" indent="-285750">
                                    <a:buFont typeface="Arial"/>
                                    <a:buChar char="•"/>
                                </a:pPr>
                                <a:r>
                                    <a:rPr lang="en-US" sz="1800" b="0">
                                        <a:solidFill><a:srgbClr val="{body_hex}"/></a:solidFill>
                                        <a:latin typeface="Segoe UI" pitchFamily="34" charset="0"/>
                                    </a:rPr>
                                    <a:t>{escaped_b}</a:t>
                                </a:r>
                            </a:p>""")

                        # Custom Content and Title shapes
                        content_shapes = f"""
                        <p:sp>
                            <p:nvSpPr><p:cNvPr id="{100 + idx}" name="Slide Title"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
                            <p:spPr>
                                <a:xfrm><a:off x="548640" y="750000"/><a:ext cx="8500000" cy="800000"/></a:xfrm>
                                <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
                                <a:noFill/>
                            </p:spPr>
                            <p:txBody>
                                <a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0"/>
                                <a:lstStyle/>
                                <a:p>
                                    <a:r>
                                        <a:rPr lang="en-US" sz="2800" b="1">
                                            <a:solidFill><a:srgbClr val="{title_hex}"/></a:solidFill>
                                            <a:latin typeface="Segoe UI" pitchFamily="34" charset="0"/>
                                        </a:rPr>
                                        <a:t>{escaped_title}</a:t>
                                    </a:r>
                                </a:p>
                            </p:txBody>
                        </p:sp>
                        <p:sp>
                            <p:nvSpPr><p:cNvPr id="{200 + idx}" name="Slide Bullets"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
                            <p:spPr>
                                <a:xfrm><a:off x="548640" y="1750000"/><a:ext cx="8500000" cy="4200000"/></a:xfrm>
                                <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
                                <a:noFill/>
                            </p:spPr>
                            <p:txBody>
                                <a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0"/>
                                <a:lstStyle/>
                                {''.join(bullet_xml_parts)}
                            </p:txBody>
                        </p:sp>
                        """
                        
                        # Replace slide number and inject content shapes
                        cloned_slide_xml = slide1_xml_str
                        # Update slide number in Text 7
                        cloned_slide_xml = re.sub(
                            r'(<p:cNvPr[^>]*name="Text 7"[^>]*>[\s\S]*?<a:t>)[^<]*(</a:t>)',
                            rf'\g<1>{seq_str}\g<2>',
                            cloned_slide_xml
                        )
                        # Inject title and bullets before </p:spTree>
                        cloned_slide_xml = cloned_slide_xml.replace('</p:spTree>', f'{content_shapes}</p:spTree>')
                        
                        zip_out.writestr(f"ppt/slides/slide{idx + 1}.xml", cloned_slide_xml.encode('utf-8'))
                        zip_out.writestr(f"ppt/slides/_rels/slide{idx + 1}.xml.rels", slide1_rels_str.encode('utf-8'))
                        
                    # [Content_Types].xml
                    ct_overrides = "".join([f'<Override PartName="/ppt/slides/slide{i+1}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>' for i in range(num_slides)])
                    content_types = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="png" ContentType="image/png"/>
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
    <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
    <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
    <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
    {ct_overrides}
</Types>"""
                    zip_out.writestr("[Content_Types].xml", content_types)
                    
                    # ppt/presentation.xml
                    sld_ids = "".join([f'<p:sldId id="{256+i}" r:id="rId{i+2}"/>' for i in range(num_slides)])
                    pres_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" 
                xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" 
                xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>
    <p:sldIdLst>{sld_ids}</p:sldIdLst>
    <p:sldSz cx="12192000" cy="6858000" type="screen16x9"/>
    <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>"""
                    zip_out.writestr("ppt/presentation.xml", pres_xml)
                    
                    # ppt/_rels/presentation.xml.rels
                    slide_rels = "".join([f'<Relationship Id="rId{i+2}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i+1}.xml"/>' for i in range(num_slides)])
                    pres_rels = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
    {slide_rels}
</Relationships>"""
                    zip_out.writestr("ppt/_rels/presentation.xml.rels", pres_rels)
                    
                    # _rels/.rels
                    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>"""
                    zip_out.writestr("_rels/.rels", root_rels)
                    
                logger.info(f"Successfully generated template-cloned presentation with {num_slides} slides at {output_path}")
                return slides
            except Exception as e:
                logger.warning(f"Template cloning fallback warning: {e}. Generating clean standard deck...")

        # Fallback if template is not found
        return PureXmlPptxBuilder._build_standard_fallback(slides, output_path, title_hex, body_hex, accent_hex, bg_hex)

    @staticmethod
    def _build_standard_fallback(slides, output_path, title_hex, body_hex, accent_hex, bg_hex):
        num_slides = len(slides)
        slide_xml_templates = []
        for idx, slide_model in enumerate(slides):
            bullet_xml_parts = []
            for b in slide_model.bullets:
                escaped_b = b.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
                bullet_xml_parts.append(f"""<a:p>
                    <a:pPr marL="285750" indent="-285750"><a:buFont typeface="Arial"/><a:buChar char="•"/></a:pPr>
                    <a:r><a:rPr lang="en-US" sz="1800" b="0"><a:solidFill><a:srgbClr val="{body_hex}"/></a:solidFill></a:rPr><a:t>{escaped_b}</a:t></a:r>
                </a:p>""")
            
            escaped_title = slide_model.title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
            seq_num = f"{idx + 1:02d}"
            
            slide_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <p:cSld>
        <p:bg><p:bgPr><a:solidFill><a:srgbClr val="{bg_hex}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>
        <p:spTree>
            <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
            <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
            <p:sp>
                <p:nvSpPr><p:cNvPr id="2" name="Badge"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
                <p:spPr>
                    <a:xfrm><a:off x="548640" y="457200"/><a:ext cx="750000" cy="400000"/></a:xfrm>
                    <a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val 25000"/></a:avLst></a:prstGeom>
                    <a:solidFill><a:srgbClr val="{accent_hex}"/></a:solidFill>
                </p:spPr>
                <p:txBody>
                    <a:bodyPr vert="horz" lIns="45720" tIns="45720" rIns="45720" bIns="45720" anchor="ctr"/>
                    <a:lstStyle/>
                    <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="1300" b="1"><a:solidFill><a:srgbClr val="000000"/></a:solidFill></a:rPr><a:t>{seq_num}</a:t></a:r></a:p>
                </p:txBody>
            </p:sp>
            <p:sp>
                <p:nvSpPr><p:cNvPr id="3" name="Title"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
                <p:spPr>
                    <a:xfrm><a:off x="1450000" y="457200"/><a:ext cx="9800000" cy="650000"/></a:xfrm>
                    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
                    <a:noFill/>
                </p:spPr>
                <p:txBody>
                    <a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0"/>
                    <a:lstStyle/>
                    <a:p><a:r><a:rPr lang="en-US" sz="2600" b="1"><a:solidFill><a:srgbClr val="{title_hex}"/></a:solidFill></a:rPr><a:t>{escaped_title}</a:t></a:r></a:p>
                </p:txBody>
            </p:sp>
            <p:sp>
                <p:nvSpPr><p:cNvPr id="4" name="Content"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
                <p:spPr>
                    <a:xfrm><a:off x="548640" y="1400000"/><a:ext cx="10800000" cy="4800000"/></a:xfrm>
                    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
                    <a:noFill/>
                </p:spPr>
                <p:txBody>
                    <a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0"/>
                    <a:lstStyle/>
                    {''.join(bullet_xml_parts)}
                </p:txBody>
            </p:sp>
        </p:spTree>
    </p:cSld>
</p:sld>"""
            slide_xml_templates.append(slide_xml)
            
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
            ct_overrides = "".join([f'<Override PartName="/ppt/slides/slide{i+1}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>' for i in range(num_slides)])
            content_types = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
    {ct_overrides}
</Types>"""
            zip_out.writestr("[Content_Types].xml", content_types)
            
            root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>"""
            zip_out.writestr("_rels/.rels", root_rels)
            
            sld_ids = "".join([f'<p:sldId id="{256+i}" r:id="rId{i+1}"/>' for i in range(num_slides)])
            pres_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
    <p:sldIdLst>{sld_ids}</p:sldIdLst>
    <p:sldSz cx="12192000" cy="6858000" type="screen16x9"/>
</p:presentation>"""
            zip_out.writestr("ppt/presentation.xml", pres_xml)
            
            slide_rels = "".join([f'<Relationship Id="rId{i+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i+1}.xml"/>' for i in range(num_slides)])
            pres_rels = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    {slide_rels}
</Relationships>"""
            zip_out.writestr("ppt/_rels/presentation.xml.rels", pres_rels)
            
            for idx, sxml in enumerate(slide_xml_templates):
                zip_out.writestr(f"ppt/slides/slide{idx + 1}.xml", sxml.encode('utf-8'))
                
        return slides


class PptxBuilder:
    """
    Presentation Builder that automatically builds beautiful presentations using the official Mintbook template.
    """
    def build(
        self,
        units: list[TeachingUnit],
        narration_segments: list[NarrationSegment],
        output_dir: str,
        template_path: str | None = None,
        title_color: str | None = None,
        body_color: str | None = None,
        accent_color: str | None = None,
        bg_color: str | None = None
    ) -> tuple[list[Slide], str]:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "output.pptx")
        narration_map = {seg.unit_id: seg.narration_text for seg in narration_segments}
        
        t_hex = hex_to_clean_hex(title_color, "FFFFFF")
        b_hex = hex_to_clean_hex(body_color, "E2E8F0")
        a_hex = hex_to_clean_hex(accent_color, "14B8A6")
        bg_hex = hex_to_clean_hex(bg_color, "0B3436")
        
        slides = PureXmlPptxBuilder.build_pptx(
            units=units,
            narration_map=narration_map,
            output_path=output_path,
            template_path=template_path,
            title_hex=t_hex,
            body_hex=b_hex,
            accent_hex=a_hex,
            bg_hex=bg_hex
        )
        
        for slide in slides:
            slide_file = os.path.join(output_dir, f"slide_{slide.unit_id}.json")
            with open(slide_file, "w", encoding="utf-8") as f:
                f.write(slide.model_dump_json(indent=2))
                
        return slides, output_path
