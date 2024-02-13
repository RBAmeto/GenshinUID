import asyncio
from pathlib import Path
from typing import Union

from PIL import Image, ImageDraw
from gsuid_core.logger import logger
from gsuid_core.utils.error_reply import get_error_img
from gsuid_core.utils.api.mys.models import MihoyoAvatar

from ..utils.mys_api import mys_api
from ..utils.image.convert import convert_img
from ..utils.resource.download_url import download_file
from ..utils.fonts.genshin_fonts import gs_font_22, gs_font_28, gs_font_40
from ..utils.resource.RESOURCE_PATH import (
    REL_PATH,
    CHAR_PATH,
    WEAPON_PATH,
    CHAR_STAND_PATH,
)
from ..utils.image.image_tools import (
    get_level_pic,
    get_simple_bg,
    get_fetter_pic,
    get_talent_pic,
    get_weapon_pic,
)

# 确定路径
TEXT_PATH = Path(__file__).parent / 'texture2d'


# 打开图片
char_card_bg4 = Image.open(TEXT_PATH / 'char_card_bg4.png')
char_card_bg5 = Image.open(TEXT_PATH / 'char_card_bg5.png')
char_card_fg = Image.open(TEXT_PATH / 'char_card_fg.png')
char_card_mask = Image.open(TEXT_PATH / 'char_card_mask.png')
role_info_fg = Image.open(TEXT_PATH / 'role_info_fg.png')

char_card8_bg4 = Image.open(TEXT_PATH / 'char_card8_bg4.png')
char_card8_bg5 = Image.open(TEXT_PATH / 'char_card8_bg5.png')
char_card8_fg = Image.open(TEXT_PATH / 'char_card8_fg.png')
char_card8_mask = Image.open(TEXT_PATH / 'char_card8_mask.png')


# 文字颜色
text_color = (68, 66, 64)


async def _draw_char_full_pic(
    img: Image.Image, char_data: MihoyoAvatar, index: int
):
    result = Image.new('RGBA', (250, 150), (0, 0, 0, 0))
    char_card_img = Image.new('RGBA', (250, 150), (0, 0, 0, 0))
    if char_data['rarity'] >= 5:
        char_card_img.paste(char_card_bg5, (0, 0))
    else:
        char_card_img.paste(char_card_bg4, (0, 0))
    # 确认武器路径
    weapon_pic_path = WEAPON_PATH / f'{char_data["weapon"]["name"]}.png'
    # 不存在自动下载
    if not weapon_pic_path.exists():
        await download_file(
            char_data['weapon']['icon'],
            5,
            f'{char_data["weapon"]["name"]}.png',
        )
    # 粘贴武器图片
    weapon_pic = Image.open(weapon_pic_path).convert('RGBA')
    weapon_pic_scale = weapon_pic.resize((50, 50))
    # 确认角色头像路径
    char_pic_path = CHAR_PATH / f'{char_data["id"]}.png'
    # 不存在自动下载
    if not char_pic_path.exists():
        await download_file(char_data['icon'], 1, f'{char_data["id"]}.png')
    # 粘贴角色头像
    char_img = Image.open(CHAR_PATH / f'{char_data["id"]}.png').convert('RGBA')
    # 缩放至合适大小
    char_img_scale = char_img.resize((148, 148))
    char_card_img.paste(char_img_scale, (-20, 5), char_img_scale)
    char_card_img.paste(char_card_fg, (0, 0), char_card_fg)
    # 命座和好感的图片
    fetter_pic = await get_fetter_pic(char_data['fetter'])
    talent_pic = await get_talent_pic(char_data['actived_constellation_num'])
    char_card_img.paste(fetter_pic, (17, 110), fetter_pic)
    char_card_img.paste(talent_pic, (177, 24), talent_pic)
    # 武器
    weapon_bg_pic = await get_weapon_pic(char_data['weapon']['rarity'])
    char_card_img.paste(weapon_bg_pic, (105, 83), weapon_bg_pic)
    char_card_img.paste(weapon_pic_scale, (105, 83), weapon_pic_scale)
    char_draw = ImageDraw.Draw(char_card_img)
    # 写字
    char_draw.text(
        (114, 37),
        f'Lv{char_data["level"]}',
        text_color,
        gs_font_22,
        anchor='lm',
    )
    char_draw.text(
        (162, 96),
        f'Lv{char_data["weapon"]["level"]}',
        text_color,
        gs_font_22,
        anchor='lm',
    )
    char_draw.text(
        (162, 123),
        f'精炼{char_data["weapon"]["affix_level"]}',
        text_color,
        gs_font_22,
        anchor='lm',
    )
    result.paste(char_card_img, (0, 0), char_card_mask)
    img.paste(
        result,
        (15 + (index % 4) * 265, 1525 + (index // 4) * 160),
        result,
    )


async def draw_pic(uid: str) -> Union[str, bytes]:
    raw_data = await mys_api.get_info(uid, None)

    if isinstance(raw_data, int):
        return await get_error_img(raw_data)

    # 记录数据
    if raw_data:
        char_data = raw_data['avatars']
    else:
        return '没有找到角色信息!'

    char_ids = []
    for i in char_data:
        char_ids.append(i['id'])

    char_rawdata = await mys_api.get_character(uid, char_ids)
    if isinstance(char_rawdata, int):
        return await get_error_img(char_rawdata)
    char_datas = char_rawdata['avatars']

    for index, i in enumerate(char_datas):
        if i['rarity'] > 5:
            char_datas[index]['rarity'] = 3
            break

    char_datas.sort(
        key=lambda x: (
            -x['rarity'],
            -x['fetter'],
            -x['actived_constellation_num'],
        )
    )

    # 确定角色占用行数
    char_num = len(char_datas)
    char_hang = (
        1 + (char_num - 1) // 4
        if char_num > 8
        else (char_num // 2) + (char_num % 2)
    )

    up_lenth = 1500

    # 获取背景图片各项参数
    based_w = 1080
    if char_num > 8:
        based_h = up_lenth + char_hang * 160 + 50
    else:
        based_h = up_lenth + char_hang * 260 + 50

    img = await get_simple_bg(based_w, based_h)
    white_overlay = Image.new('RGBA', (based_w, based_h), (255, 251, 242, 211))
    img.paste(white_overlay, (0, 0), white_overlay)
    char_import = Image.open(
        CHAR_STAND_PATH / f'{char_datas[0]["id"]}.png'
    ).convert('RGBA')
    img.paste(char_import, (-540, -180), char_import)
    img.paste(role_info_fg, (0, 0), role_info_fg)

    # 绘制基础信息文字
    text_draw = ImageDraw.Draw(img)
    text_draw.text((65, 468), f'UID{uid}', text_color, gs_font_40, anchor='lm')
    # 已获角色
    text_draw.text(
        (1024, 569),
        str(raw_data['stats']['avatar_number']),
        text_color,
        gs_font_40,
        anchor='rm',
    )
    # 活跃天数
    text_draw.text(
        (1024, 294),
        str(raw_data['stats']['active_day_number']),
        text_color,
        gs_font_40,
        anchor='rm',
    )
    # 成就数量
    text_draw.text(
        (1024, 386),
        str(raw_data['stats']['achievement_number']),
        text_color,
        gs_font_40,
        anchor='rm',
    )
    # 深渊
    text_draw.text(
        (1024, 477),
        raw_data['stats']['spiral_abyss'],
        text_color,
        gs_font_40,
        anchor='rm',
    )

    # 世界探索
    world_exp = raw_data['world_explorations']
    world_list = []
    # 须弥占坑 & 城市补足
    for city_index in range(1, 15):
        if city_index in [11, 12]:
            continue
        world_list.append(
            {
                'id': city_index,
                'exp': ['0.0%'],
                'extra': [{'name': '等阶', 'level': 0}],
            }
        )
    for world_part in world_exp:
        # 添加探索值
        temp = {
            'id': world_part['id'],
            'exp': [f'{world_part["exploration_percentage"] / 10}%'],
            'extra': [{'name': '等阶', 'level': world_part['level']}],
        }
        # 添加属性值
        for offering in world_part['offerings']:
            temp['extra'].append(
                {'name': offering['name'], 'level': offering['level']}
            )

        # 岚丹特色怪物计数
        count = 1
        for offering in world_part['boss_list']:
            temp['extra'].append(
                {'name': offering['name'], 'level': offering['kill_num']}
            )
            count += 1
            if count >= 3:
                break

        if world_part['id'] == 13:
            _id = 10
        else:
            _id = world_part['id'] - 1
        world_list[_id] = temp

    world_list.sort(key=lambda x: (-x['id']), reverse=True)
    # 添加宝箱信息和锚点
    chest_data = [
        'common_chest_number',
        'exquisite_chest_number',
        'precious_chest_number',
        'luxurious_chest_number',
        'magic_chest_number',
        'way_point_number',
        'domain_number',
    ]
    for status_index, status in enumerate(chest_data):
        world_list.append(
            {
                'id': 500 + status_index,
                'exp': [str(raw_data['stats'][status])],
                'extra': [],
            }
        )
    task = []

    if (
        'homes' in raw_data
        and raw_data['homes']
        and 'comfort_num' in raw_data['homes'][0]
    ):
        world_list.append(
            {
                'id': 1000,
                'exp': [str(raw_data['homes'][0]['comfort_num'])],
                'extra': [],
            }
        )

    for world_index, world in enumerate(world_list):
        task.append(_draw_world_exp_pic(img, text_draw, world, world_index))
    await asyncio.gather(*task)

    tasks = []
    if char_num > 8:
        for index, char in enumerate(char_datas):
            tasks.append(
                _draw_char_full_pic(
                    img,
                    char,
                    index,
                )
            )
    else:
        for index, char in enumerate(char_datas):
            tasks.append(
                _draw_char_8_pic(
                    img,
                    char,
                    index,
                )
            )
    await asyncio.gather(*tasks)

    res = await convert_img(img)
    logger.info('[查询角色信息]绘图已完成,等待发送!')
    return res


async def _draw_world_exp_pic(
    img: Image.Image,
    text_draw: ImageDraw.ImageDraw,
    world: dict,
    world_index: int,
):
    offset_x = 258
    offset_y = 171
    for world_exp_index, world_exp in enumerate(world['exp']):
        if world['extra']:
            size = gs_font_28
            pos_y = 694
        else:
            size = gs_font_40
            pos_y = 708
        text_draw.text(
            (
                260 + world_index % 4 * offset_x,
                pos_y + world_index // 4 * offset_y + world_exp_index * 28,
            ),
            world_exp,
            text_color,
            size,
            anchor='rm',
        )
    for offering_index, offering in enumerate(world['extra']):
        if offering["name"] == "等阶":
            level_pic = await get_level_pic(offering["level"])
            img.paste(
                level_pic,
                (
                    199 + world_index % 4 * offset_x,
                    650 + world_index // 4 * offset_y,
                ),
                level_pic,
            )
        else:
            text_draw.text(
                (
                    260 + world_index % 4 * offset_x,
                    (len(world['exp']) - 1) * 28
                    + 696
                    + world_index // 4 * offset_y
                    + offering_index * 23,
                ),
                f'{str(offering["name"])}:{str(offering["level"])}',
                text_color,
                gs_font_22,
                anchor='rm',
            )


async def _draw_char_8_pic(
    img: Image.Image, char_data: MihoyoAvatar, index: int
):
    """
    绘制8人角色图片
    """
    result = Image.new('RGBA', (510, 225), (0, 0, 0, 0))
    char_card_img = Image.new('RGBA', (510, 225), (0, 0, 0, 0))
    if char_data['rarity'] >= 5:
        char_card_img.paste(char_card8_bg5, (0, 0))
    else:
        char_card_img.paste(char_card8_bg4, (0, 0))
    # 确认武器路径
    weapon_pic_path = WEAPON_PATH / f'{char_data["weapon"]["name"]}.png'
    # 不存在自动下载
    if not weapon_pic_path.exists():
        await download_file(
            char_data['weapon']['icon'],
            5,
            f'{char_data["weapon"]["name"]}.png',
        )
    # 粘贴武器图片
    weapon_pic = Image.open(weapon_pic_path).convert('RGBA')
    weapon_pic_scale = weapon_pic.resize((50, 50))
    # 确认角色头像路径
    char_pic_path = CHAR_PATH / f'{char_data["id"]}.png'
    # 不存在自动下载
    if not char_pic_path.exists():
        await download_file(char_data['icon'], 1, f'{char_data["id"]}.png')
    # 粘贴角色图片
    char_img = Image.open(CHAR_PATH / f'{char_data["id"]}.png').convert('RGBA')

    # 角色立绘
    char_stand_img = Image.open(
        CHAR_STAND_PATH / f'{char_data["id"]}.png'
    ).convert('RGBA')
    char_stand_img.putalpha(
        char_stand_img.getchannel('A').point(
            lambda x: round(x * 0.4) if x > 0 else 0
        )
    )
    char_card_img.paste(char_stand_img, (-912, -313), char_stand_img)
    char_card_img.paste(char_img, (-14, -28), char_img)
    char_card_img.paste(char_card8_fg, (0, 0), char_card8_fg)
    fetter_pic = await get_fetter_pic(char_data['fetter'])
    talent_pic = await get_talent_pic(char_data['actived_constellation_num'])
    weapon_bg_pic = await get_weapon_pic(char_data['weapon']['rarity'])
    char_card_img.paste(fetter_pic, (355, 27), fetter_pic)
    char_card_img.paste(talent_pic, (435, 24), talent_pic)
    char_card_img.paste(weapon_bg_pic, (21, 158), weapon_bg_pic)
    char_card_img.paste(weapon_pic_scale, (21, 158), weapon_pic_scale)
    for equip_index, equip in enumerate(char_data['reliquaries']):
        equip_bg = await get_weapon_pic(equip['rarity'])
        equip_pic = (
            Image.open(REL_PATH / f'{equip["name"]}.png')
            .convert('RGBA')
            .resize((50, 50))
        )
        char_card_img.paste(equip_bg, (242 + equip_index * 50, 170), equip_bg)
        char_card_img.paste(
            equip_pic, (242 + equip_index * 50, 170), equip_pic
        )
    char_draw = ImageDraw.Draw(char_card_img)
    char_draw.text(
        (254, 36),
        f'Lv{char_data["level"]}',
        text_color,
        gs_font_40,
        anchor='lm',
    )
    char_draw.text(
        (81, 196),
        f'Lv{char_data["weapon"]["level"]}',
        text_color,
        gs_font_22,
        anchor='lm',
    )
    char_draw.text(
        (81, 168),
        f'{char_data["weapon"]["name"]}',
        text_color,
        gs_font_22,
        anchor='lm',
    )
    char_draw.text(
        (138, 196),
        f'精炼{char_data["weapon"]["affix_level"]}',
        text_color,
        gs_font_22,
        anchor='lm',
    )
    result.paste(char_card_img, (0, 0), char_card8_mask)
    img.paste(
        result,
        (15 + (index % 2) * 520, 1525 + (index // 2) * 250),
        result,
    )
