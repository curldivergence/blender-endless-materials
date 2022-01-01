import bpy
import glob
import os

TILES_BASE_COLOR_PATH = "D:/textures/base_color_*.png"
TILES_NORMAL_PATH = "D:/textures/normal_*.png"
TILES_HEIGHT_PATH = "D:/textures/height_*.png"
RANDOM_TEXTURE_PATH = "D:/textures/random.png"
MAT_NAME = "EndlessMaterial"
MAX_TILES = 10
NORMAL_FORMAT = "DX"

def create_tile_nodes(texture_group, tile_tex_files, node_tree):
    nodes = node_tree.nodes

    if texture_group == "BASE_COLOR":
        y_offset = -500
    elif texture_group == "NORMAL":
        y_offset = -500 - len(tile_tex_files) * 300
    elif texture_group == "HEIGHT":
        y_offset = -500 - len(tile_tex_files) * 300 * 2

    tile_tex_nodes = []
    for tile_tex_idx, tile_tex in enumerate(tile_tex_files):
        tile_tex_node = nodes.new(type="ShaderNodeTexImage")
        tile_tex_node.location = (0, y_offset - 300 * tile_tex_idx)
        tile_tex_node.image = bpy.data.images.load(tile_tex)
        tile_tex_nodes.append(tile_tex_node)

    compare_nodes = []
    compare_nodes.append(nodes.new(type="ShaderNodeMath"))
    compare_nodes[-1].location = (2500, y_offset)
    compare_nodes[-1].operation = "COMPARE"
    compare_nodes[-1].inputs[1].default_value = 0
    compare_nodes[-1].inputs[2].default_value = 1e-3

    node_tree.links.new(compare_nodes[-1].inputs[0], nodes["Modulo"].outputs["Value"])

    mix_nodes = []
    mix_nodes.append(nodes.new(type="ShaderNodeMixRGB"))
    mix_nodes[-1].location = (2800, y_offset)

    node_tree.links.new(mix_nodes[-1].inputs[0], compare_nodes[-1].outputs["Value"])
    node_tree.links.new(mix_nodes[-1].inputs[1], tile_tex_nodes[0].outputs["Color"])

    for tile_tex_idx in range(1, len(tile_tex_nodes) - 1):
        node_tree.links.new(mix_nodes[-1].inputs[2], tile_tex_nodes[tile_tex_idx].outputs["Color"])

        compare_nodes.append(nodes.new(type="ShaderNodeMath"))
        compare_nodes[-1].location = (2800 + 300 * tile_tex_idx, y_offset - 300 * tile_tex_idx)
        compare_nodes[-1].operation = "COMPARE"
        compare_nodes[-1].inputs[1].default_value = tile_tex_idx
        compare_nodes[-1].inputs[2].default_value = 1e-3

        node_tree.links.new(compare_nodes[-1].inputs[0], nodes["Modulo"].outputs["Value"])

        mix_nodes.append(nodes.new(type="ShaderNodeMixRGB"))
        mix_nodes[-1].location = (3100 + 300 * tile_tex_idx, y_offset - 300 * tile_tex_idx)

        node_tree.links.new(mix_nodes[-1].inputs[1], mix_nodes[-2].outputs["Color"])

        node_tree.links.new(mix_nodes[-1].inputs[0], compare_nodes[-1].outputs["Value"])

    node_tree.links.new(mix_nodes[-1].inputs[2], tile_tex_nodes[-1].outputs["Color"])

    if texture_group == "BASE_COLOR":
        node_tree.links.new(nodes["Principled BSDF"].inputs["Base Color"], mix_nodes[-1].outputs["Color"])
    elif texture_group == "NORMAL":
        normal_conv_loc = mix_nodes[-1].location

        if NORMAL_FORMAT == "DX":
            sep_xyz_node = nodes.new(type="ShaderNodeSeparateXYZ")
            sep_xyz_node.location = (normal_conv_loc[0] + 300, normal_conv_loc[1])

            node_tree.links.new(sep_xyz_node.inputs[0], mix_nodes[-1].outputs["Color"])

            comb_xyz_node = nodes.new(type="ShaderNodeCombineXYZ")
            comb_xyz_node.location = (normal_conv_loc[0] + 800, normal_conv_loc[1])

            node_tree.links.new(comb_xyz_node.inputs["X"], sep_xyz_node.outputs["X"])
            node_tree.links.new(comb_xyz_node.inputs["Z"], sep_xyz_node.outputs["Z"])

            sub_y_node = nodes.new(type="ShaderNodeMath")
            sub_y_node.location = (normal_conv_loc[0] + 550, normal_conv_loc[1] - 150)
            sub_y_node.operation = "SUBTRACT"
            sub_y_node.inputs[0].default_value = 1

            node_tree.links.new(sub_y_node.inputs[1], sep_xyz_node.outputs["Y"])
            node_tree.links.new(comb_xyz_node.inputs["Y"], sub_y_node.outputs["Value"])

            norm_map_node = nodes.new(type="ShaderNodeNormalMap")
            norm_map_node.location = (normal_conv_loc[0] + 1100, normal_conv_loc[1])

            node_tree.links.new(norm_map_node.inputs["Color"], comb_xyz_node.outputs[0])
        elif NORMAL_FORMAT == "OGL":
            norm_map_node = nodes.new(type="ShaderNodeNormalMap")
            norm_map_node.location = (normal_conv_loc[0] + 300, normal_conv_loc[1])

            node_tree.links.new(norm_map_node.inputs["Color"], mix_nodes[-1].outputs["Color"])
        else:
            assert False

        node_tree.links.new(nodes["Principled BSDF"].inputs["Normal"], norm_map_node.outputs["Normal"])

    elif texture_group == "HEIGHT":
        disp_conv_loc = mix_nodes[-1].location

        disp_node = nodes.new(type="ShaderNodeDisplacement")
        disp_node.location = (disp_conv_loc[0] + 300, disp_conv_loc[1])
        disp_node.inputs["Scale"].default_value = 0.5

        node_tree.links.new(disp_node.inputs["Height"], mix_nodes[-1].outputs["Color"])

        node_tree.links.new(nodes["Material Output"].inputs["Displacement"], disp_node.outputs["Displacement"])


for mat in bpy.data.materials:
    if mat.name == MAT_NAME:
        bpy.data.materials.remove(mat)

base_color_tiles = glob.glob(TILES_BASE_COLOR_PATH)[:MAX_TILES]
normal_tiles = glob.glob(TILES_NORMAL_PATH)[:MAX_TILES]
height_tiles = glob.glob(TILES_HEIGHT_PATH)[:MAX_TILES]

for image in bpy.data.images:
    if image.filepath in base_color_tiles or image.filepath in normal_tiles \
        or image.filepath in height_tiles:
        bpy.data.images.remove(image)

tile_tex_count = len(base_color_tiles)

mat = bpy.data.materials.new(name=MAT_NAME)
mat.use_nodes = True
mat.cycles.displacement_method = "DISPLACEMENT"

node_tree = mat.node_tree
nodes = node_tree.nodes

tex_coord_node = nodes.new(type="ShaderNodeTexCoord")
tex_coord_node.location = (0, 0)

sep_xyz_node = nodes.new(type="ShaderNodeSeparateXYZ")
sep_xyz_node.location = (300, 0)

node_tree.links.new(sep_xyz_node.inputs["Vector"], tex_coord_node.outputs["UV"])

floor_x_node = nodes.new(type="ShaderNodeMath")
floor_x_node.location = (600, 300)
floor_x_node.operation = "FLOOR"

node_tree.links.new(floor_x_node.inputs["Value"], sep_xyz_node.outputs["X"])

floor_y_node = nodes.new(type="ShaderNodeMath")
floor_y_node.location = (600, -300)
floor_y_node.operation = "FLOOR"

node_tree.links.new(floor_y_node.inputs["Value"], sep_xyz_node.outputs["Y"])

divide_x_node = nodes.new(type="ShaderNodeMath")
divide_x_node.location = (900, 300)
divide_x_node.operation = "DIVIDE"

node_tree.links.new(divide_x_node.inputs[0], floor_x_node.outputs["Value"])

divide_y_node = nodes.new(type="ShaderNodeMath")
divide_y_node.location = (900, -300)
divide_y_node.operation = "DIVIDE"
divide_y_node.inputs[1].default_value = 1

node_tree.links.new(divide_y_node.inputs[0], floor_y_node.outputs["Value"])

comb_xyz_node = nodes.new(type="ShaderNodeCombineXYZ")
comb_xyz_node.location = (1200, 0)

node_tree.links.new(comb_xyz_node.inputs["X"], divide_x_node.outputs["Value"])
node_tree.links.new(comb_xyz_node.inputs["Y"], divide_y_node.outputs["Value"])

rand_tex_node = nodes.new(type="ShaderNodeTexImage")
rand_tex_node.location = (1500, 0)
rand_tex_node.image = bpy.data.images.load(RANDOM_TEXTURE_PATH)
rand_tex_node.interpolation = "Closest"

divide_x_node.inputs[1].default_value = rand_tex_node.image.size[0]
divide_y_node.inputs[1].default_value = rand_tex_node.image.size[1]

node_tree.links.new(rand_tex_node.inputs["Vector"], comb_xyz_node.outputs["Vector"])

multiply_rand_node = nodes.new(type="ShaderNodeMath")
multiply_rand_node.location = (1900, 0)
multiply_rand_node.operation = "MULTIPLY"
multiply_rand_node.inputs[1].default_value = tile_tex_count - 1

node_tree.links.new(multiply_rand_node.inputs[0], rand_tex_node.outputs["Color"])

round_rand_node = nodes.new(type="ShaderNodeMath")
round_rand_node.location = (2200, 0)
round_rand_node.operation = "ROUND"

node_tree.links.new(round_rand_node.inputs["Value"], multiply_rand_node.outputs["Value"])

modulo_rand_node = nodes.new(type="ShaderNodeMath")
modulo_rand_node.name = "Modulo"
modulo_rand_node.location = (2400, 0)
modulo_rand_node.operation = "MODULO"
modulo_rand_node.inputs[1].default_value = 255

node_tree.links.new(modulo_rand_node.inputs["Value"], round_rand_node.outputs["Value"])

create_tile_nodes("BASE_COLOR", base_color_tiles, node_tree)
create_tile_nodes("NORMAL", normal_tiles, node_tree)
create_tile_nodes("HEIGHT", height_tiles, node_tree)

bsdf_node = nodes["Principled BSDF"]
bsdf_node.location = (3500 + 300 * tile_tex_count, 0)

output_node = nodes["Material Output"]
output_node.location = (3800 + 300 * tile_tex_count, 0)
