// 无人机城市低空仿真世界前端：负责数据加载、三维显示、交互选中与验证视角控制。
const ROUTE_SELECTION_PAGE_CONFIG = window.ROUTE_SELECTION_PAGE_CONFIG || {};

const DATASETS = {
  procedural: {
    name: "urban_grid_world",
    summary: "../outputs/urban_grid_world/world_summary.json",
    world: "../outputs/urban_grid_world/world.geojson",
    route: "../outputs/urban_grid_world/route.czml",
    routeType: "czml",
  },
  manhattan: {
    name: "manhattan_midtown",
    summary: "../outputs/real_city/manhattan_midtown/city_summary.json",
    world: "../outputs/real_city/manhattan_midtown/real_buildings.geojson",
    route: "../outputs/real_city/manhattan_midtown/route.geojson",
    ground: null,
    weather: "../outputs/real_city/manhattan_midtown/real_weather_field.geojson",
    tileset: "../outputs/real_city/manhattan_midtown/tiles/tileset.json",
    groundTileset: "../outputs/real_city/manhattan_midtown/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/manhattan_midtown/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  chicago: {
    name: "chicago_loop",
    summary: "../outputs/real_city/chicago_loop/city_summary.json",
    world: "../outputs/real_city/chicago_loop/real_buildings.geojson",
    route: "../outputs/real_city/chicago_loop/route.geojson",
    ground: null,
    weather: "../outputs/real_city/chicago_loop/real_weather_field.geojson",
    tileset: "../outputs/real_city/chicago_loop/tiles/tileset.json",
    groundTileset: "../outputs/real_city/chicago_loop/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/chicago_loop/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  london: {
    name: "london_canary_wharf",
    summary: "../outputs/real_city/london_canary_wharf/city_summary.json",
    world: "../outputs/real_city/london_canary_wharf/real_buildings.geojson",
    route: "../outputs/real_city/london_canary_wharf/route.geojson",
    ground: null,
    weather: "../outputs/real_city/london_canary_wharf/real_weather_field.geojson",
    tileset: "../outputs/real_city/london_canary_wharf/tiles/tileset.json",
    groundTileset: "../outputs/real_city/london_canary_wharf/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/london_canary_wharf/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  tokyo: {
    name: "tokyo_shinjuku",
    summary: "../outputs/real_city/tokyo_shinjuku/city_summary.json",
    world: "../outputs/real_city/tokyo_shinjuku/real_buildings.geojson",
    route: "../outputs/real_city/tokyo_shinjuku/route.geojson",
    ground: null,
    weather: "../outputs/real_city/tokyo_shinjuku/real_weather_field.geojson",
    tileset: "../outputs/real_city/tokyo_shinjuku/tiles/tileset.json",
    groundTileset: "../outputs/real_city/tokyo_shinjuku/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/tokyo_shinjuku/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  singapore: {
    name: "singapore_marina_bay",
    summary: "../outputs/real_city/singapore_marina_bay/city_summary.json",
    world: "../outputs/real_city/singapore_marina_bay/real_buildings.geojson",
    route: "../outputs/real_city/singapore_marina_bay/route.geojson",
    ground: null,
    weather: "../outputs/real_city/singapore_marina_bay/real_weather_field.geojson",
    tileset: "../outputs/real_city/singapore_marina_bay/tiles/tileset.json",
    groundTileset: "../outputs/real_city/singapore_marina_bay/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/singapore_marina_bay/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  shanghai: {
    name: "shanghai_lujiazui",
    summary: "../outputs/real_city/shanghai_lujiazui/city_summary.json",
    world: "../outputs/real_city/shanghai_lujiazui/real_buildings.geojson",
    route: "../outputs/real_city/shanghai_lujiazui/route.geojson",
    ground: null,
    weather: "../outputs/real_city/shanghai_lujiazui/real_weather_field.geojson",
    tileset: "../outputs/real_city/shanghai_lujiazui/tiles/tileset.json",
    groundTileset: "../outputs/real_city/shanghai_lujiazui/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/shanghai_lujiazui/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  shenzhen: {
    name: "shenzhen_futian",
    summary: "../outputs/real_city/shenzhen_futian/city_summary.json",
    world: "../outputs/real_city/shenzhen_futian/real_buildings.geojson",
    route: "../outputs/real_city/shenzhen_futian/route.geojson",
    ground: null,
    weather: "../outputs/real_city/shenzhen_futian/real_weather_field.geojson",
    tileset: "../outputs/real_city/shenzhen_futian/tiles/tileset.json",
    groundTileset: "../outputs/real_city/shenzhen_futian/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/shenzhen_futian/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  guangzhou: {
    name: "guangzhou_zhujiang_new_town",
    summary: "../outputs/real_city/guangzhou_zhujiang_new_town/city_summary.json",
    world: "../outputs/real_city/guangzhou_zhujiang_new_town/real_buildings.geojson",
    route: "../outputs/real_city/guangzhou_zhujiang_new_town/route.geojson",
    ground: null,
    weather: "../outputs/real_city/guangzhou_zhujiang_new_town/real_weather_field.geojson",
    tileset: "../outputs/real_city/guangzhou_zhujiang_new_town/tiles/tileset.json",
    groundTileset: "../outputs/real_city/guangzhou_zhujiang_new_town/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/guangzhou_zhujiang_new_town/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  beijing: {
    name: "beijing_cbd_guomao",
    summary: "../outputs/real_city/beijing_cbd_guomao/city_summary.json",
    world: "../outputs/real_city/beijing_cbd_guomao/real_buildings.geojson",
    route: "../outputs/real_city/beijing_cbd_guomao/route.geojson",
    ground: null,
    weather: "../outputs/real_city/beijing_cbd_guomao/real_weather_field.geojson",
    tileset: "../outputs/real_city/beijing_cbd_guomao/tiles/tileset.json",
    groundTileset: "../outputs/real_city/beijing_cbd_guomao/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/beijing_cbd_guomao/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  chongqing: {
    name: "chongqing_jiefangbei",
    summary: "../outputs/real_city/chongqing_jiefangbei/city_summary.json",
    world: "../outputs/real_city/chongqing_jiefangbei/real_buildings.geojson",
    route: "../outputs/real_city/chongqing_jiefangbei/route.geojson",
    ground: null,
    weather: "../outputs/real_city/chongqing_jiefangbei/real_weather_field.geojson",
    tileset: "../outputs/real_city/chongqing_jiefangbei/tiles/tileset.json",
    groundTileset: "../outputs/real_city/chongqing_jiefangbei/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/chongqing_jiefangbei/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  hangzhou: {
    name: "hangzhou_qianjiang",
    summary: "../outputs/real_city/hangzhou_qianjiang/city_summary.json",
    world: "../outputs/real_city/hangzhou_qianjiang/real_buildings.geojson",
    route: "../outputs/real_city/hangzhou_qianjiang/route.geojson",
    ground: null,
    weather: "../outputs/real_city/hangzhou_qianjiang/real_weather_field.geojson",
    tileset: "../outputs/real_city/hangzhou_qianjiang/tiles/tileset.json",
    groundTileset: "../outputs/real_city/hangzhou_qianjiang/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/hangzhou_qianjiang/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  chengdu: {
    name: "chengdu_tianfu_square",
    summary: "../outputs/real_city/chengdu_tianfu_square/city_summary.json",
    world: "../outputs/real_city/chengdu_tianfu_square/real_buildings.geojson",
    route: "../outputs/real_city/chengdu_tianfu_square/route.geojson",
    ground: null,
    weather: "../outputs/real_city/chengdu_tianfu_square/real_weather_field.geojson",
    tileset: "../outputs/real_city/chengdu_tianfu_square/tiles/tileset.json",
    groundTileset: "../outputs/real_city/chengdu_tianfu_square/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/chengdu_tianfu_square/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  wuhan: {
    name: "wuhan_guanggu",
    summary: "../outputs/real_city/wuhan_guanggu/city_summary.json",
    world: "../outputs/real_city/wuhan_guanggu/real_buildings.geojson",
    route: "../outputs/real_city/wuhan_guanggu/route.geojson",
    ground: null,
    weather: "../outputs/real_city/wuhan_guanggu/real_weather_field.geojson",
    tileset: "../outputs/real_city/wuhan_guanggu/tiles/tileset.json",
    groundTileset: "../outputs/real_city/wuhan_guanggu/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/wuhan_guanggu/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  wuhan_central_urban: {
    name: "wuhan_central_urban",
    summary: "../outputs/real_city/wuhan_central_urban/city_summary.json",
    world: "../outputs/real_city/wuhan_central_urban/real_buildings.geojson",
    route: "../outputs/real_city/wuhan_central_urban/route.geojson",
    ground: null,
    weather: "../outputs/real_city/wuhan_central_urban/real_weather_field.geojson",
    tileset: "../outputs/real_city/wuhan_central_urban/tiles/tileset.json",
    groundTileset: "../outputs/real_city/wuhan_central_urban/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/wuhan_central_urban/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  wuhan_jianghan: {
    name: "wuhan_jianghan",
    summary: "../outputs/real_city/wuhan_jianghan/city_summary.json",
    world: "../outputs/real_city/wuhan_jianghan/real_buildings.geojson",
    route: "../outputs/real_city/wuhan_jianghan/route.geojson",
    ground: null,
    weather: "../outputs/real_city/wuhan_jianghan/real_weather_field.geojson",
    tileset: "../outputs/real_city/wuhan_jianghan/tiles/tileset.json",
    groundTileset: "../outputs/real_city/wuhan_jianghan/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/wuhan_jianghan/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  wuhan_wuchang: {
    name: "wuhan_wuchang",
    summary: "../outputs/real_city/wuhan_wuchang/city_summary.json",
    world: "../outputs/real_city/wuhan_wuchang/real_buildings.geojson",
    route: "../outputs/real_city/wuhan_wuchang/route.geojson",
    ground: null,
    weather: "../outputs/real_city/wuhan_wuchang/real_weather_field.geojson",
    tileset: "../outputs/real_city/wuhan_wuchang/tiles/tileset.json",
    groundTileset: "../outputs/real_city/wuhan_wuchang/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/wuhan_wuchang/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  nanjing: {
    name: "nanjing_xinjiekou",
    summary: "../outputs/real_city/nanjing_xinjiekou/city_summary.json",
    world: "../outputs/real_city/nanjing_xinjiekou/real_buildings.geojson",
    route: "../outputs/real_city/nanjing_xinjiekou/route.geojson",
    ground: null,
    weather: "../outputs/real_city/nanjing_xinjiekou/real_weather_field.geojson",
    tileset: "../outputs/real_city/nanjing_xinjiekou/tiles/tileset.json",
    groundTileset: "../outputs/real_city/nanjing_xinjiekou/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/nanjing_xinjiekou/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  hongkong: {
    name: "hongkong_central",
    summary: "../outputs/real_city/hongkong_central/city_summary.json",
    world: "../outputs/real_city/hongkong_central/real_buildings.geojson",
    route: "../outputs/real_city/hongkong_central/route.geojson",
    ground: null,
    weather: "../outputs/real_city/hongkong_central/real_weather_field.geojson",
    tileset: "../outputs/real_city/hongkong_central/tiles/tileset.json",
    groundTileset: "../outputs/real_city/hongkong_central/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/hongkong_central/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  shenzhen_nanshan_tech: {
    name: "shenzhen_nanshan_tech",
    summary: "../outputs/real_city/shenzhen_nanshan_tech/city_summary.json",
    world: "../outputs/real_city/shenzhen_nanshan_tech/real_buildings.geojson",
    route: "../outputs/real_city/shenzhen_nanshan_tech/route.geojson",
    ground: null,
    weather: "../outputs/real_city/shenzhen_nanshan_tech/real_weather_field.geojson",
    tileset: "../outputs/real_city/shenzhen_nanshan_tech/tiles/tileset.json",
    groundTileset: "../outputs/real_city/shenzhen_nanshan_tech/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/shenzhen_nanshan_tech/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  shenzhen_qianhai: {
    name: "shenzhen_qianhai",
    summary: "../outputs/real_city/shenzhen_qianhai/city_summary.json",
    world: "../outputs/real_city/shenzhen_qianhai/real_buildings.geojson",
    route: "../outputs/real_city/shenzhen_qianhai/route.geojson",
    ground: null,
    weather: "../outputs/real_city/shenzhen_qianhai/real_weather_field.geojson",
    tileset: "../outputs/real_city/shenzhen_qianhai/tiles/tileset.json",
    groundTileset: "../outputs/real_city/shenzhen_qianhai/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/shenzhen_qianhai/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  shanghai_people_square: {
    name: "shanghai_people_square",
    summary: "../outputs/real_city/shanghai_people_square/city_summary.json",
    world: "../outputs/real_city/shanghai_people_square/real_buildings.geojson",
    route: "../outputs/real_city/shanghai_people_square/route.geojson",
    ground: null,
    weather: "../outputs/real_city/shanghai_people_square/real_weather_field.geojson",
    tileset: "../outputs/real_city/shanghai_people_square/tiles/tileset.json",
    groundTileset: "../outputs/real_city/shanghai_people_square/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/shanghai_people_square/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  shanghai_xujiahui: {
    name: "shanghai_xujiahui",
    summary: "../outputs/real_city/shanghai_xujiahui/city_summary.json",
    world: "../outputs/real_city/shanghai_xujiahui/real_buildings.geojson",
    route: "../outputs/real_city/shanghai_xujiahui/route.geojson",
    ground: null,
    weather: "../outputs/real_city/shanghai_xujiahui/real_weather_field.geojson",
    tileset: "../outputs/real_city/shanghai_xujiahui/tiles/tileset.json",
    groundTileset: "../outputs/real_city/shanghai_xujiahui/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/shanghai_xujiahui/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  beijing_wangjing: {
    name: "beijing_wangjing",
    summary: "../outputs/real_city/beijing_wangjing/city_summary.json",
    world: "../outputs/real_city/beijing_wangjing/real_buildings.geojson",
    route: "../outputs/real_city/beijing_wangjing/route.geojson",
    ground: null,
    weather: "../outputs/real_city/beijing_wangjing/real_weather_field.geojson",
    tileset: "../outputs/real_city/beijing_wangjing/tiles/tileset.json",
    groundTileset: "../outputs/real_city/beijing_wangjing/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/beijing_wangjing/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  beijing_zhongguancun: {
    name: "beijing_zhongguancun",
    summary: "../outputs/real_city/beijing_zhongguancun/city_summary.json",
    world: "../outputs/real_city/beijing_zhongguancun/real_buildings.geojson",
    route: "../outputs/real_city/beijing_zhongguancun/route.geojson",
    ground: null,
    weather: "../outputs/real_city/beijing_zhongguancun/real_weather_field.geojson",
    tileset: "../outputs/real_city/beijing_zhongguancun/tiles/tileset.json",
    groundTileset: "../outputs/real_city/beijing_zhongguancun/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/beijing_zhongguancun/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  guangzhou_pazhou: {
    name: "guangzhou_pazhou",
    summary: "../outputs/real_city/guangzhou_pazhou/city_summary.json",
    world: "../outputs/real_city/guangzhou_pazhou/real_buildings.geojson",
    route: "../outputs/real_city/guangzhou_pazhou/route.geojson",
    ground: null,
    weather: "../outputs/real_city/guangzhou_pazhou/real_weather_field.geojson",
    tileset: "../outputs/real_city/guangzhou_pazhou/tiles/tileset.json",
    groundTileset: "../outputs/real_city/guangzhou_pazhou/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/guangzhou_pazhou/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  chengdu_financial_city: {
    name: "chengdu_financial_city",
    summary: "../outputs/real_city/chengdu_financial_city/city_summary.json",
    world: "../outputs/real_city/chengdu_financial_city/real_buildings.geojson",
    route: "../outputs/real_city/chengdu_financial_city/route.geojson",
    ground: null,
    weather: "../outputs/real_city/chengdu_financial_city/real_weather_field.geojson",
    tileset: "../outputs/real_city/chengdu_financial_city/tiles/tileset.json",
    groundTileset: "../outputs/real_city/chengdu_financial_city/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/chengdu_financial_city/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  chongqing_jiangbeizui: {
    name: "chongqing_jiangbeizui",
    summary: "../outputs/real_city/chongqing_jiangbeizui/city_summary.json",
    world: "../outputs/real_city/chongqing_jiangbeizui/real_buildings.geojson",
    route: "../outputs/real_city/chongqing_jiangbeizui/route.geojson",
    ground: null,
    weather: "../outputs/real_city/chongqing_jiangbeizui/real_weather_field.geojson",
    tileset: "../outputs/real_city/chongqing_jiangbeizui/tiles/tileset.json",
    groundTileset: "../outputs/real_city/chongqing_jiangbeizui/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/chongqing_jiangbeizui/tiles/outline_tileset.json",
    routeType: "geojson",
  },
  suzhou_jinji_lake: {
    name: "suzhou_jinji_lake",
    summary: "../outputs/real_city/suzhou_jinji_lake/city_summary.json",
    world: "../outputs/real_city/suzhou_jinji_lake/real_buildings.geojson",
    route: "../outputs/real_city/suzhou_jinji_lake/route.geojson",
    ground: null,
    weather: "../outputs/real_city/suzhou_jinji_lake/real_weather_field.geojson",
    tileset: "../outputs/real_city/suzhou_jinji_lake/tiles/tileset.json",
    groundTileset: "../outputs/real_city/suzhou_jinji_lake/tiles/ground_tileset.json",
    outlineTileset: "../outputs/real_city/suzhou_jinji_lake/tiles/outline_tileset.json",
    routeType: "geojson",
  },
};

Cesium.Ion.defaultAccessToken = "";

const CORRECTION_VERSION_LIST_URL = "../outputs/real_city_corrections/version_index.json";
const RADIO_PROFILE_URLS = {
  manhattan: "../outputs/radio_route_inputs/manhattan_midtown_scale_2p5m/route_radio_profile.json",
  wuhan_central_urban: "../outputs/radio_route_inputs/wuhan_central_urban_default/route_radio_profile.json",
};
const RADIO_TEXTURE_TILE_URLS = {
  manhattan: "../outputs/radio_route_inputs/manhattan_midtown_scale_2p5m/heatmaps/texture_tile_index.json",
};
const RADIO_POINT_CLOUD_URLS = {
  manhattan: {
    sparse: "../outputs/radio_route_inputs/manhattan_midtown_scale_2p5m/heatmaps/radio_point_cloud_step32.json",
    standard: "../outputs/radio_route_inputs/manhattan_midtown_scale_2p5m/heatmaps/radio_point_cloud_step16.json",
    dense: "../outputs/radio_route_inputs/manhattan_midtown_scale_2p5m/heatmaps/radio_point_cloud_step8.json",
    ultra: "../outputs/radio_route_inputs/manhattan_midtown_scale_2p5m/heatmaps/radio_point_cloud_step4.json",
    extreme: "../outputs/radio_route_inputs/manhattan_midtown_scale_2p5m/heatmaps/radio_point_cloud_step2.json",
  },
};
const RADIO_POINT_CLOUD_DENSITIES = {
  sparse: { label: "稀疏", text: "原始密度的 1/1024", baseSize: 9.0, gainSize: 6.0 },
  standard: { label: "标准", text: "原始密度的 1/256", baseSize: 7.0, gainSize: 5.0 },
  dense: { label: "较密", text: "原始密度的 1/64", baseSize: 4.8, gainSize: 3.2 },
  ultra: { label: "高密", text: "原始密度的 1/16", baseSize: 2.8, gainSize: 2.0 },
  extreme: { label: "极密", text: "原始密度的 1/4", baseSize: 1.7, gainSize: 1.0 },
};
const BUILDING_CLASS_OPTIONS = {
  building: { label: "建筑", color: "#00d0ff" },
  road: { label: "道路/车行道", color: "#5f6c7b" },
  pedestrian: { label: "步行区域/人行道", color: "#c0a46b" },
  green: { label: "绿化草坪/公园", color: "#2a9d8f" },
  plaza: { label: "广场/铺装空地", color: "#e9c46a" },
  water: { label: "水体", color: "#277da1" },
  parking: { label: "停车场", color: "#6c757d" },
  construction: { label: "施工/裸地", color: "#bc6c25" },
  transport_facility: { label: "交通设施", color: "#577590" },
  transport_elevated: { label: "交通立体结构", color: "#9c6644" },
  transport_support: { label: "交通支撑结构", color: "#4d6a6d" },
  other_ground: { label: "其他地面要素", color: "#8fa7a0" },
  suspect: { label: "疑似误识别/待复核", color: "#b83b31" },
};
const FULL_HEIGHT_CITY_FEATURE_CLASSES = new Set(["building", "transport_elevated", "transport_support"]);
const LOW_CITY_FEATURE_HEIGHT_M = {
  road: 0.16,
  pedestrian: 0.20,
  green: 0.35,
  plaza: 0.22,
  water: 0.08,
  parking: 0.18,
  construction: 0.45,
  transport_facility: 0.55,
  other_ground: 0.32,
  suspect: 0.45,
};
const CORRECTION_PALE_COLORS = {
  building: "#d8ddd7",
  road: "#c8ccd0",
  pedestrian: "#d7cfbf",
  green: "#c4dcc8",
  plaza: "#ded7c5",
  water: "#bcd7e0",
  parking: "#c9ced0",
  construction: "#dcc7b5",
  transport_facility: "#c8d1da",
  transport_elevated: "#d9c8b6",
  transport_support: "#c8d4d5",
  other_ground: "#cad5d0",
  suspect: "#d9c3c0",
};
const CORRECTION_MUTED_COLORS = {
  building: "#8fb3c4",
  road: "#7a8288",
  pedestrian: "#b7a47f",
  green: "#79ad8f",
  plaza: "#c7b071",
  water: "#6fa4ba",
  parking: "#899196",
  construction: "#b68560",
  transport_facility: "#728ba2",
  transport_elevated: "#b08a68",
  transport_support: "#6f8c90",
  other_ground: "#91aaa0",
  suspect: "#b86f67",
};
const CORRECTION_CONTRAST_COLORS = {
  building: "#00c8ff",
  road: "#2f3640",
  pedestrian: "#ffbf3f",
  green: "#13a538",
  plaza: "#ffd43b",
  water: "#1c7ed6",
  parking: "#495057",
  construction: "#f76707",
  transport_facility: "#4263eb",
  transport_elevated: "#d9480f",
  transport_support: "#0b7285",
  other_ground: "#5c7c6b",
  suspect: "#e03131",
};

const ROUTE_DRAFT_API_URL = "/api/route-drafts";
const WORKBENCH_SETTINGS_API_URL = "/api/workbench-settings";
const ASSET_VERSION = new URLSearchParams(window.location.search).get("v") || "dev";
const mapWrap = document.querySelector(".map-wrap");

function assetUrl(url) {
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}v=${encodeURIComponent(ASSET_VERSION)}`;
}

const viewer = new Cesium.Viewer("cesiumContainer", {
  animation: false,
  timeline: false,
  baseLayerPicker: false,
  geocoder: false,
  homeButton: false,
  sceneModePicker: true,
  navigationHelpButton: false,
  fullscreenButton: true,
  fullscreenElement: mapWrap || document.body,
  infoBox: false,
  selectionIndicator: true,
  baseLayer: false,
  terrainProvider: new Cesium.EllipsoidTerrainProvider(),
  orderIndependentTranslucency: false,
});
window.viewer = viewer;

function installFullscreenFallback() {
  const fullscreenButton = document.querySelector(".cesium-fullscreenButton");
  if (!fullscreenButton || !mapWrap) return;
  fullscreenButton.addEventListener("click", (event) => {
    if (!document.fullscreenEnabled) return;
    event.stopPropagation();
    event.preventDefault();
    if (document.fullscreenElement === mapWrap) {
      document.exitFullscreen?.().catch(() => {});
      return;
    }
    mapWrap.requestFullscreen?.().catch(() => {});
  }, true);
  document.addEventListener("fullscreenchange", () => {
    resizeViewerSoon();
  });
}

installFullscreenFallback();

viewer.scene.globe.depthTestAgainstTerrain = false;
viewer.scene.skyAtmosphere.show = false;
viewer.scene.fog.enabled = false;
viewer.scene.backgroundColor = Cesium.Color.fromCssColorString("#eef1ec");
if (viewer.scene.skyBox) {
  viewer.scene.skyBox.show = false;
}
if (viewer.scene.sun) {
  viewer.scene.sun.show = false;
}
if (viewer.scene.moon) {
  viewer.scene.moon.show = false;
}
if (viewer.scene.globe) {
  viewer.scene.globe.enableLighting = true;
  viewer.scene.globe.show = false;
  viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString("#eef1ec");
  viewer.scene.globe.showGroundAtmosphere = false;
}
if ("shadows" in viewer) {
  viewer.shadows = false;
}
if ("sunBloom" in viewer.scene) {
  viewer.scene.sunBloom = false;
}
viewer.imageryLayers.removeAll();
viewer.camera.frustum.near = 0.2;
viewer.scene.screenSpaceCameraController.minimumZoomDistance = 80.0;
viewer.scene.screenSpaceCameraController.maximumZoomDistance = 18000.0;
viewer.scene.screenSpaceCameraController.enableRotate = false;
viewer.scene.screenSpaceCameraController.enableTilt = false;
viewer.scene.screenSpaceCameraController.enableTranslate = true;
viewer.scene.screenSpaceCameraController.enableZoom = false;
viewer.scene.screenSpaceCameraController.enableLook = true;
viewer.scene.screenSpaceCameraController.tiltEventTypes = [
  Cesium.CameraEventType.PINCH,
];
viewer.scene.screenSpaceCameraController.rotateEventTypes = [
  Cesium.CameraEventType.RIGHT_DRAG,
];
viewer.scene.screenSpaceCameraController.translateEventTypes = [
  Cesium.CameraEventType.MIDDLE_DRAG,
];
viewer.scene.screenSpaceCameraController.zoomEventTypes = [
  Cesium.CameraEventType.WHEEL,
  Cesium.CameraEventType.PINCH,
];

const state = {
  worldSource: null,
  routeSource: null,
  groundSource: null,
  tileset: null,
  groundTileset: null,
  outlineTileset: null,
  osmBuildings: null,
  center: null,
  worldCenter: null,
  worldBounds: null,
  routeFocus: null,
  routeFeature: null,
  routePrimitives: null,
  radioProfile: null,
  radioProfileEntities: [],
  radioProfileImageryLayers: [],
  radioProfilePointCloud: null,
  radioProfilePointCloudData: null,
  radioProfilePointCloudDatasetKey: null,
  radioProfileSettings: { last: null, datasets: {} },
  radioProfileSettingsLoaded: false,
  radioProfilePendingSampleFilter: "all",
  routeDraft: {
    drawing: false,
    points: [],
    preview: null,
    lineEntity: null,
    groundEntity: null,
    pointEntities: [],
    dirty: false,
    savedVersion: null,
  },
  weatherPrimitives: null,
  buildingIndex: [],
  selectedBuilding: null,
  multiSelectedBuildings: [],
  buildingClassifications: {},
  correctionDirty: false,
  correctionVersion: "default",
  allCorrectionVersions: [],
  correctionVersions: [],
  correctionDefaultVersions: {},
  correctionDefaultVersion: "default",
  correctionDefaultColorModes: {},
  correctionDefaultColorMode: "category",
  correctionColorMode: "category",
  classEditorTouched: false,
  deleteConfirmVersion: null,
  classificationEntities: [],
  selectionEntity: null,
  selectionEntities: [],
  multiSelectionEntities: [],
  buildingEntities: [],
  groundEntities: [],
  noFlyEntities: [],
  weatherEntities: [],
  weatherFeatures: [],
  weatherVisibleCount: 0,
  routeEntities: [],
  sunEntities: [],
  orbit: {
    dragging: false,
    lastX: 0,
    lastY: 0,
    startX: 0,
    startY: 0,
    moved: false,
    headingDeg: 32,
    pitchDeg: -26,
    rangeM: 1850,
  },
  sunTimer: null,
};

const $ = (id) => document.getElementById(id);
const appShell = document.querySelector(".app-shell");

if (ROUTE_SELECTION_PAGE_CONFIG.defaultDatasetKey && $("dataset-select")) {
  const defaultOption = $("dataset-select").querySelector(`option[value="${ROUTE_SELECTION_PAGE_CONFIG.defaultDatasetKey}"]`);
  if (defaultOption) {
    $("dataset-select").value = ROUTE_SELECTION_PAGE_CONFIG.defaultDatasetKey;
  }
}

function setStatus(text) {
  $("load-status").textContent = text;
}

function resizeViewerSoon() {
  setTimeout(() => viewer.resize(), 260);
}

function updatePanelToggleButtons() {
  const leftCollapsed = appShell.classList.contains("left-collapsed");
  const rightCollapsed = appShell.classList.contains("right-collapsed");
  $("btn-toggle-left").textContent = leftCollapsed ? ">" : "<";
  $("btn-toggle-left").setAttribute("aria-expanded", String(!leftCollapsed));
  $("btn-toggle-left").setAttribute("aria-label", leftCollapsed ? "展开左侧栏" : "折叠左侧栏");
  $("btn-toggle-right").textContent = rightCollapsed ? "<" : ">";
  $("btn-toggle-right").setAttribute("aria-expanded", String(!rightCollapsed));
  $("btn-toggle-right").setAttribute("aria-label", rightCollapsed ? "展开右侧栏" : "折叠右侧栏");
}

function togglePanel(side) {
  appShell.classList.toggle(`${side}-collapsed`);
  updatePanelToggleButtons();
  resizeViewerSoon();
}

function datasetConfig(datasetKey = currentDatasetKey()) {
  return DATASETS[datasetKey] || {};
}

function versionMatchesDataset(version, datasetKey = currentDatasetKey()) {
  if (!version || version.id === "default") return true;
  const dataset = datasetConfig(datasetKey);
  const generated = version.generatedTiles || {};
  return (
    version.datasetKey === datasetKey ||
    generated.datasetKey === datasetKey ||
    version.cityName === dataset.name ||
    generated.cityName === dataset.name
  );
}

function defaultVersionForDataset(datasetKey = currentDatasetKey(), versions = state.correctionVersions) {
  const ids = new Set(versions.map((version) => version.id));
  const candidates = [
    state.correctionDefaultVersions?.[datasetKey],
    versionMatchesDataset(state.allCorrectionVersions.find((version) => version.id === state.correctionDefaultVersion), datasetKey)
      ? state.correctionDefaultVersion
      : null,
    "default",
  ];
  return candidates.find((candidate) => candidate && ids.has(candidate)) || "default";
}

function validCorrectionColorMode(mode) {
  const select = $("building-class-color-mode");
  if (!select) return mode || "category";
  return [...select.options].some((option) => option.value === mode) ? mode : "category";
}

function defaultColorModeForDataset(datasetKey = currentDatasetKey()) {
  return validCorrectionColorMode(
    state.correctionDefaultColorModes?.[datasetKey] ||
    state.correctionDefaultColorMode ||
    "category"
  );
}

function applyDefaultCorrectionColorMode(datasetKey = currentDatasetKey()) {
  const mode = defaultColorModeForDataset(datasetKey);
  const select = $("building-class-color-mode");
  if (select) select.value = mode;
  state.correctionColorMode = mode;
}

function refreshCorrectionVersionSelect(preferredVersion = null) {
  const select = $("building-class-version");
  if (!select) return;
  const fallbackDefault = { id: "default", label: "原始版本", path: "default.json" };
  const filtered = state.allCorrectionVersions.filter((version) => versionMatchesDataset(version));
  if (!filtered.some((version) => version.id === "default")) {
    filtered.unshift(fallbackDefault);
  }
  state.correctionVersions = filtered.length ? filtered : [fallbackDefault];
  const datasetDefault = defaultVersionForDataset(currentDatasetKey(), state.correctionVersions);
  const candidate = preferredVersion || datasetDefault;
  const selected = state.correctionVersions.some((version) => version.id === candidate) ? candidate : datasetDefault;
  select.innerHTML = "";
  state.correctionVersions.forEach((version) => {
    const option = document.createElement("option");
    option.value = version.id;
    option.textContent = version.id === datasetDefault
      ? `${version.label || version.id}（默认）`
      : (version.label || version.id);
    select.appendChild(option);
  });
  select.value = selected;
  state.correctionVersion = selected;
  updateCorrectionSaveControls();
}

async function loadCorrectionVersionIndex(preferredVersion = null) {
  try {
    const resp = await fetch(assetUrl(CORRECTION_VERSION_LIST_URL), { cache: "no-store" });
    if (!resp.ok) throw new Error("no correction index");
    const index = await resp.json();
    state.correctionDefaultVersion = index.defaultVersion || "default";
    state.correctionDefaultVersions = index.defaultVersions || {};
    state.correctionDefaultColorMode = validCorrectionColorMode(index.defaultColorMode || "category");
    state.correctionDefaultColorModes = index.defaultColorModes || {};
    state.allCorrectionVersions = Array.isArray(index.versions) && index.versions.length
      ? index.versions
      : [{ id: "default", label: "原始版本", path: "default.json" }];
  } catch (error) {
    state.correctionDefaultVersion = "default";
    state.correctionDefaultVersions = {};
    state.correctionDefaultColorMode = "category";
    state.correctionDefaultColorModes = {};
    state.allCorrectionVersions = [{ id: "default", label: "原始版本", path: "default.json" }];
  }
  refreshCorrectionVersionSelect(preferredVersion);
}

function correctionVersionUrl(versionId) {
  const version = state.correctionVersions.find((item) => item.id === versionId);
  const path = version?.path || `${versionId}.json`;
  return `../outputs/real_city_corrections/${path}`;
}

function correctedTileAssetPaths(dataset) {
  if (!dataset?.name || !state.correctionVersion || state.correctionVersion === "default") return null;
  const version = state.correctionVersions.find((item) => item.id === state.correctionVersion);
  const generated = version?.generatedTiles;
  if (!generated || generated.cityName !== dataset.name || Number(generated.removedCount || 0) <= 0) return null;
  const tileVersion = generated.version || version.localVersion || state.correctionVersion;
  const base = `../outputs/real_city/${dataset.name}/corrected_tiles/${tileVersion}`;
  return {
    tileset: `${base}/tileset.json`,
    groundTileset: `${base}/ground_tileset.json`,
    outlineTileset: `${base}/outline_tileset.json`,
  };
}

function resolveTileAssets(dataset) {
  return correctedTileAssetPaths(dataset) || dataset;
}

async function loadBuildingClassifications() {
  const versionId = $("building-class-version")?.value || state.correctionDefaultVersion || "default";
  state.correctionVersion = versionId;
  try {
    const resp = await fetch(assetUrl(correctionVersionUrl(versionId)), { cache: "no-store" });
    if (!resp.ok) throw new Error("no correction version");
    const payload = await resp.json();
    state.buildingClassifications = payload.records || {};
    state.correctionDirty = false;
  } catch (error) {
    state.buildingClassifications = {};
    state.correctionDirty = false;
  }
}

function updateIonDependentControls() {
  const token = $("ion-token").value.trim();
  const hasToken = Boolean(token);
  const osmOption = $("building-backend").querySelector('option[value="osm"]');
  const worldTerrainOption = $("terrain-mode").querySelector('option[value="world"]');
  if (osmOption) {
    osmOption.disabled = !hasToken;
    osmOption.textContent = hasToken ? "Cesium OSM Buildings" : "Cesium OSM Buildings（需 Token）";
  }
  if (worldTerrainOption) {
    worldTerrainOption.disabled = !hasToken;
    worldTerrainOption.textContent = hasToken ? "Cesium World Terrain" : "Cesium World Terrain（需 Token）";
  }
  if (!hasToken && $("building-backend").value === "osm") {
    $("building-backend").value = "tiles";
  }
  if (!hasToken && $("terrain-mode").value === "world") {
    $("terrain-mode").value = "ellipsoid";
  }
  if ($("ion-hint")) {
    $("ion-hint").textContent = hasToken
      ? "Token 已填写：可尝试加载 Cesium 在线建筑或真实地形。"
      : "未配置 Token：使用本地建筑和本地平面基底。";
  }
}

document.querySelectorAll("summary").forEach((summary) => {
  summary.addEventListener("mousedown", (event) => {
    if (event.detail > 1) event.preventDefault();
  });
  summary.addEventListener("selectstart", (event) => event.preventDefault());
});

function setAmbientOcclusion(enabled) {
  const ao = viewer.scene.postProcessStages?.ambientOcclusion;
  if (!ao) return;
  ao.enabled = enabled;
  if (ao.uniforms) {
    ao.uniforms.intensity = enabled ? 0.10 : 0.0;
    ao.uniforms.bias = 0.09;
    ao.uniforms.lengthCap = 0.18;
    ao.uniforms.stepSize = 1.1;
  }
}

function weatherGridMode() {
  return $("weather-grid-mode")?.value || "full";
}

function weatherAltitudeMode() {
  return $("weather-altitude-mode")?.value || "all";
}

function optionText(selectId, value) {
  const option = $(`${selectId}`)?.querySelector(`option[value="${value}"]`);
  return option?.textContent?.trim() || value;
}

function weatherGridVisible(feature) {
  const gridMode = weatherGridMode();
  const gx = Number(feature.properties?.grid_x ?? 0);
  const gy = Number(feature.properties?.grid_y ?? 0);
  if (gridMode === "medium") {
    return gx % 2 === 0 && gy % 2 === 0;
  }
  if (gridMode === "corridor") {
    return gy === 2 || gy === 3;
  }
  if (gridMode === "sparse") {
    return gx % 3 === 0 && gy % 2 === 0;
  }
  return true;
}

function weatherAltitudeVisible(feature) {
  const altitudeMode = weatherAltitudeMode();
  const altitude = String(feature.properties?.altitude_m ?? "");
  if (altitudeMode === "low") {
    return ["30", "60", "100"].includes(altitude);
  }
  if (altitudeMode === "mission") {
    return ["100", "150", "220"].includes(altitude);
  }
  return true;
}

function weatherFeatureVisible(feature) {
  const altitudeFilter = $("altitude-filter")?.value || "all";
  const featureAltitude = String(feature.properties?.altitude_m ?? "");
  return (
    weatherGridVisible(feature) &&
    weatherAltitudeVisible(feature) &&
    (altitudeFilter === "all" || altitudeFilter === featureAltitude)
  );
}

function updateWeatherResolutionSummary() {
  const total = state.weatherFeatures.length;
  const visible = state.weatherVisibleCount;
  const gridLabel = optionText("weather-grid-mode", weatherGridMode());
  const altitudeLabel = optionText("weather-altitude-mode", weatherAltitudeMode());
  const label = total
    ? `当前显示 ${visible}/${total} 个天气采样点；派生网格 ${gridLabel}，高度层 ${altitudeLabel}。`
    : "等待加载天气场。";
  if ($("weather-resolution-summary")) {
    $("weather-resolution-summary").textContent = label;
  }
  if ($("stat-weather")) {
    $("stat-weather").textContent = total ? `${visible}/${total}` : "--";
  }
}

function setShadowQuality(enabled) {
  if (!("shadows" in viewer)) return;
  viewer.shadows = enabled;
  if (viewer.shadowMap) {
    viewer.shadowMap.enabled = enabled;
    viewer.shadowMap.softShadows = true;
    viewer.shadowMap.normalOffset = true;
    if ("size" in viewer.shadowMap) {
      viewer.shadowMap.size = enabled ? 4096 : viewer.shadowMap.size;
    }
    viewer.shadowMap.darkness = enabled ? 0.74 : 0.0;
    viewer.shadowMap.maximumDistance = enabled ? 1600.0 : 0.0;
  }
}

function createWeatherPrimitive(feature) {
  const coords = feature.geometry.coordinates;
  const altitude = Number(coords[2] ?? feature.properties?.altitude_m ?? 100.0);
  const p = Cesium.Cartesian3.fromDegrees(coords[0], coords[1], Number.isFinite(altitude) ? altitude : 100.0);
  const turbulence = Number(feature.properties?.turbulence_index || 0.2);
  const properties = {
    ...(feature.properties || {}),
    lon: Number(Number(coords[0]).toFixed(7)),
    lat: Number(Number(coords[1]).toFixed(7)),
    altitude_m: Number.isFinite(altitude) ? altitude : 100.0,
  };
  return {
    position: p,
    pixelSize: 4 + turbulence * 7,
    color: Cesium.Color.fromCssColorString(
      turbulence > 0.72 ? "#d1495b" : turbulence > 0.45 ? "#f4a261" : "#2a9d8f"
    ).withAlpha(0.8),
    outlineColor: Cesium.Color.WHITE.withAlpha(0.4),
    outlineWidth: 1,
    id: {
      uavFeature: {
        type: "weather",
        label: "天气采样点",
        properties,
        coordinates: [coords[0], coords[1], properties.altitude_m],
      },
    },
  };
}

function currentSunLocalHour() {
  const mode = $("sun-cycle")?.value || "auto";
  const cycleMs = 60 * 60 * 1000;
  const fraction = mode === "noon" ? 0.5 : (Date.now() % cycleMs) / cycleMs;
  return 6 + fraction * 12;
}

function offsetLonLat(center, eastM, northM) {
  const latRad = Cesium.Math.toRadians(center.lat);
  return {
    lon: center.lon + eastM / (111320.0 * Math.max(0.2, Math.cos(latRad))),
    lat: center.lat + northM / 111320.0,
  };
}

function cityRadiusM(center, bounds) {
  if (!center || !bounds) return 1500.0;
  const latScale = 111320.0;
  const lonScale = latScale * Math.max(0.2, Math.cos(Cesium.Math.toRadians(center.lat)));
  const corners = [
    [bounds.west, bounds.south],
    [bounds.east, bounds.south],
    [bounds.east, bounds.north],
    [bounds.west, bounds.north],
  ];
  return Math.max(...corners.map(([lon, lat]) => {
    const eastM = (lon - center.lon) * lonScale;
    const northM = (lat - center.lat) * latScale;
    return Math.hypot(eastM, northM);
  }));
}

function clearSunMarker() {
  state.sunEntities.forEach((entity) => viewer.entities.remove(entity));
  state.sunEntities = [];
}

function updateSunMarker(localHour = currentSunLocalHour()) {
  clearSunMarker();
  if ($("lighting-mode")?.value !== "sun") return;
  const center = state.worldCenter || state.center;
  if (!center) return;
  const fraction = Math.max(0.0, Math.min(1.0, (localHour - 6.0) / 12.0));
  const azimuthDeg = 90.0 + fraction * 180.0;
  const azimuthRad = Cesium.Math.toRadians(azimuthDeg);
  const radiusM = cityRadiusM(center, state.worldBounds);
  const distanceM = Math.max(1300.0, Math.min(3200.0, radiusM + 120.0));
  const lineStartM = Math.max(radiusM - 150.0, distanceM - 240.0);
  const start = offsetLonLat(center, Math.sin(azimuthRad) * lineStartM, Math.cos(azimuthRad) * lineStartM);
  const marker = offsetLonLat(center, Math.sin(azimuthRad) * distanceM, Math.cos(azimuthRad) * distanceM);
  const labelOnLeft = Math.sin(azimuthRad) >= 0.0;
  const lineColor = Cesium.Color.fromCssColorString("#f5b342").withAlpha(0.88);
  state.sunEntities.push(viewer.entities.add({
    polyline: {
      positions: Cesium.Cartesian3.fromDegreesArrayHeights([
        start.lon, start.lat, 3.0,
        marker.lon, marker.lat, 3.0,
      ]),
      width: 5,
      material: new Cesium.PolylineArrowMaterialProperty(lineColor),
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    },
  }));
  state.sunEntities.push(viewer.entities.add({
    position: Cesium.Cartesian3.fromDegrees(marker.lon, marker.lat, 12.0),
    point: {
      pixelSize: 22,
      color: Cesium.Color.fromCssColorString("#ffd166").withAlpha(0.94),
      outlineColor: Cesium.Color.fromCssColorString("#6f3f08"),
      outlineWidth: 3,
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    },
    label: {
      text: `太阳方向 ${localHour.toFixed(1)}时`,
      font: "700 13px Avenir Next, sans-serif",
      fillColor: Cesium.Color.fromCssColorString("#452600"),
      outlineColor: Cesium.Color.WHITE.withAlpha(0.72),
      outlineWidth: 3,
      style: Cesium.LabelStyle.FILL_AND_OUTLINE,
      verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      horizontalOrigin: labelOnLeft ? Cesium.HorizontalOrigin.RIGHT : Cesium.HorizontalOrigin.LEFT,
      pixelOffset: new Cesium.Cartesian2(labelOnLeft ? -10 : 10, -18),
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    },
  }));
}

function applySunTime() {
  if ($("lighting-mode")?.value !== "sun") return null;
  const localHour = currentSunLocalHour();
  const lon = Number((state.worldCenter || state.center)?.lon || 0);
  const utcHour = (localHour - lon / 15 + 24) % 24;
  const wholeHour = Math.floor(utcHour);
  const minutes = Math.floor((utcHour - wholeHour) * 60);
  const seconds = Math.floor((((utcHour - wholeHour) * 60) - minutes) * 60);
  const date = new Date();
  date.setUTCHours(wholeHour, minutes, seconds, 0);
  viewer.clock.currentTime = Cesium.JulianDate.fromDate(date);
  return localHour;
}

function applyLightingMode() {
  const enabled = $("lighting-mode")?.value === "sun";
  const disabled = Cesium.ShadowMode?.DISABLED;
  const castOnly = Cesium.ShadowMode?.CAST_ONLY ?? Cesium.ShadowMode?.ENABLED;
  const receiveOnly = Cesium.ShadowMode?.RECEIVE_ONLY ?? Cesium.ShadowMode?.ENABLED;
  if (viewer.scene.sun) viewer.scene.sun.show = enabled;
  if (Cesium.SunLight && ("light" in viewer.scene)) {
    viewer.scene.light = enabled ? new Cesium.SunLight() : undefined;
  }
  setShadowQuality(enabled);
  setAmbientOcclusion(enabled);
  if (state.tileset && Cesium.ShadowMode) {
    state.tileset.shadows = enabled ? castOnly : disabled;
  }
  if (state.groundTileset && Cesium.ShadowMode) {
    state.groundTileset.shadows = enabled ? receiveOnly : disabled;
  }
  if (state.outlineTileset && Cesium.ShadowMode) {
    state.outlineTileset.shadows = disabled;
  }
  if (state.osmBuildings && Cesium.ShadowMode) {
    state.osmBuildings.shadows = enabled ? castOnly : disabled;
  }
  if (state.sunTimer) {
    clearInterval(state.sunTimer);
    state.sunTimer = null;
  }
  if (enabled) {
    updateSunMarker(applySunTime() || currentSunLocalHour());
    if ($("sun-cycle")?.value === "auto") {
      state.sunTimer = setInterval(() => {
        updateSunMarker(applySunTime() || currentSunLocalHour());
      }, 5000);
    }
  } else {
    clearSunMarker();
  }
}

const interactionTarget = document.getElementById("cesiumContainer");
window.__orbitDebug = { applied: 0 };

function isCanvasPointerEvent(event) {
  return event.target === viewer.canvas;
}

interactionTarget.addEventListener("pointerdown", (event) => {
  if (event.button !== 0 || !state.center || !isCanvasPointerEvent(event)) return;
  state.orbit.dragging = true;
  state.orbit.lastX = event.clientX;
  state.orbit.lastY = event.clientY;
  state.orbit.startX = event.clientX;
  state.orbit.startY = event.clientY;
  state.orbit.moved = false;
  interactionTarget.setPointerCapture?.(event.pointerId);
  event.preventDefault();
});
window.addEventListener("pointerup", (event) => {
  const wasDragging = state.orbit.dragging;
  const wasClick = wasDragging && !state.orbit.moved;
  state.orbit.dragging = false;
  if (wasDragging && interactionTarget.hasPointerCapture?.(event.pointerId)) {
    interactionTarget.releasePointerCapture(event.pointerId);
  }
  if (wasClick) {
    handleSceneClick(event.clientX, event.clientY, { multi: event.ctrlKey || event.metaKey });
  }
});
window.addEventListener("pointermove", (event) => {
  if (state.routeDraft.drawing && !state.orbit.dragging) {
    updateRouteDraftPreview(event.clientX, event.clientY);
  }
  if (!state.orbit.dragging || !state.center) return;
  const dx = event.clientX - state.orbit.lastX;
  const dy = event.clientY - state.orbit.lastY;
  const totalDx = event.clientX - state.orbit.startX;
  const totalDy = event.clientY - state.orbit.startY;
  if (Math.hypot(totalDx, totalDy) > 4) {
    state.orbit.moved = true;
  }
  state.orbit.lastX = event.clientX;
  state.orbit.lastY = event.clientY;
  state.orbit.headingDeg = (state.orbit.headingDeg - dx * 0.18 + 360) % 360;
  state.orbit.pitchDeg = Math.max(-82, Math.min(-18, state.orbit.pitchDeg - dy * 0.12));
  applyOrbitCamera(0);
  event.preventDefault();
});
interactionTarget.addEventListener("wheel", (event) => {
  if (!state.center) return;
  const factor = event.deltaY > 0 ? 1.12 : 0.88;
  state.orbit.rangeM = Math.max(160, Math.min(9000, state.orbit.rangeM * factor));
  applyOrbitCamera(0);
  event.preventDefault();
}, { passive: false });
interactionTarget.addEventListener("contextmenu", (event) => {
  if (!state.center || !isCanvasPointerEvent(event)) return;
  event.preventDefault();
  if (state.routeDraft.drawing) return;
  handleSceneClick(event.clientX, event.clientY, { multi: true });
});

function entityLayer(entity) {
  return entity.properties?.layer?.getValue?.() || entity.properties?.layer;
}

function heightColor(height) {
  if (height >= 180) return Cesium.Color.fromCssColorString("#7a3f15");
  if (height >= 140) return Cesium.Color.fromCssColorString("#a85d25");
  if (height >= 100) return Cesium.Color.fromCssColorString("#c97a2e");
  if (height >= 70) return Cesium.Color.fromCssColorString("#d8a15b");
  if (height >= 40) return Cesium.Color.fromCssColorString("#7d9c8a");
  return Cesium.Color.fromCssColorString("#a8b6ae");
}

function riskColor(risk) {
  if (risk >= 8) return Cesium.Color.fromCssColorString("#9d1c20");
  if (risk >= 5) return Cesium.Color.fromCssColorString("#d1495b");
  if (risk >= 2.5) return Cesium.Color.fromCssColorString("#f4a261");
  return Cesium.Color.fromCssColorString("#8fa7a0");
}

function buildingRenderMode() {
  return $("render-mode")?.value || "solid";
}

function showFeatureDetail(title, props) {
  $("feature-detail").textContent = `${title}\n${JSON.stringify(props, null, 2)}`;
}

function currentDatasetKey() {
  return $("dataset-select")?.value || "unknown_dataset";
}

function buildingKey(item) {
  const props = item?.properties || {};
  if (props.osm_id !== undefined && props.osm_id !== null) {
    return `${currentDatasetKey()}:osm:${props.osm_type || "way"}:${props.osm_id}`;
  }
  if (props.id) {
    return `${currentDatasetKey()}:id:${props.id}`;
  }
  const first = item?.ring?.[0] || [0, 0];
  return `${currentDatasetKey()}:geom:${Number(first[0]).toFixed(7)}:${Number(first[1]).toFixed(7)}:${Number(item?.area || 0).toFixed(10)}`;
}

function classRecordFor(item) {
  if (!item) return null;
  return state.buildingClassifications[buildingKey(item)] || null;
}

function classCountForCurrentDataset() {
  const prefix = `${currentDatasetKey()}:`;
  return Object.keys(state.buildingClassifications).filter((key) => key.startsWith(prefix)).length;
}

function correctionPayload() {
  const datasetKey = currentDatasetKey();
  const dataset = DATASETS[datasetKey] || {};
  return {
    schema: "uav_virtual_validation_city_feature_corrections_v1",
    version: state.correctionVersion,
    datasetKey,
    cityName: dataset.name || datasetKey,
    updatedAt: new Date().toISOString(),
    records: state.buildingClassifications,
  };
}

function setBuildingClassControlsEnabled(enabled) {
  ["building-class-select", "building-class-note", "btn-apply-class", "btn-clear-class"].forEach((id) => {
    const element = $(id);
    if (element) element.disabled = !enabled;
  });
}

function selectedCorrectionTargets() {
  if (state.multiSelectedBuildings.length > 0) return state.multiSelectedBuildings;
  return state.selectedBuilding ? [state.selectedBuilding] : [];
}

function updateBuildingClassEditor() {
  const item = state.selectedBuilding;
  const multiCount = state.multiSelectedBuildings.length;
  const count = classCountForCurrentDataset();
  state.classEditorTouched = false;
  if ($("class-edit-count")) {
    const dirty = state.correctionDirty ? "（未保存）" : "";
    $("class-edit-count").textContent = `当前版本 ${state.correctionVersion}${dirty}：本世界 ${count} 个纠错项。`;
  }
  updateCorrectionSaveControls();
  if (multiCount > 0) {
    const records = state.multiSelectedBuildings.map((building) => classRecordFor(building));
    const validRecords = records.filter(Boolean);
    const sameClass = validRecords.length === multiCount && validRecords.every((record) => record.classId === validRecords[0].classId);
    const sameNote = validRecords.length === multiCount && validRecords.every((record) => (record.note || "") === (validRecords[0].note || ""));
    setBuildingClassControlsEnabled(true);
    if ($("btn-apply-class")) $("btn-apply-class").textContent = "批量应用";
    if ($("btn-clear-class")) $("btn-clear-class").textContent = "清除多选";
    if ($("building-class-select")) $("building-class-select").value = sameClass ? validRecords[0].classId : "suspect";
    if ($("building-class-note")) $("building-class-note").value = sameNote ? (validRecords[0].note || "") : "";
    if ($("class-edit-status")) {
      $("class-edit-status").textContent = `已多选 ${multiCount} 个建筑；应用纠错会批量设置这些对象，清除当前会批量移除它们的纠错记录。`;
    }
    return;
  }
  if (!item) {
    setBuildingClassControlsEnabled(false);
    if ($("btn-apply-class")) $("btn-apply-class").textContent = "应用纠错";
    if ($("btn-clear-class")) $("btn-clear-class").textContent = "清除当前";
    if ($("building-class-select")) $("building-class-select").value = "suspect";
    if ($("building-class-note")) $("building-class-note").value = "";
    if ($("class-edit-status")) {
      $("class-edit-status").textContent = "左键单选建筑；右键或 Ctrl/Command+左键可连续多选，然后批量设置城市要素。";
    }
    return;
  }
  const record = classRecordFor(item);
  setBuildingClassControlsEnabled(true);
  if ($("btn-apply-class")) $("btn-apply-class").textContent = "应用纠错";
  if ($("btn-clear-class")) $("btn-clear-class").textContent = "清除当前";
  if ($("building-class-select")) $("building-class-select").value = record?.classId || "suspect";
  if ($("building-class-note")) $("building-class-note").value = record?.note || "";
  const props = item.properties || {};
  const label = props.name || props.osm_id || props.id || "未命名建筑";
  if ($("class-edit-status")) {
    $("class-edit-status").textContent = record
      ? `已选择：${label}；当前纠错为 ${record.classLabel}。`
      : `已选择：${label}；尚未纠错。`;
  }
}

function correctionColorMode() {
  return $("building-class-color-mode")?.value || state.correctionColorMode || "category";
}

function correctionFillColor(record) {
  const mode = correctionColorMode();
  if (mode === "ground") return Cesium.Color.fromCssColorString("#c9d0c8");
  if (mode === "pale") return Cesium.Color.fromCssColorString(CORRECTION_PALE_COLORS[record?.classId] || "#d4d8d1");
  if (mode === "muted") return Cesium.Color.fromCssColorString(CORRECTION_MUTED_COLORS[record?.classId] || "#91aaa0");
  if (mode === "contrast" || mode === "outline") return Cesium.Color.fromCssColorString(CORRECTION_CONTRAST_COLORS[record?.classId] || "#e03131");
  return Cesium.Color.fromCssColorString(record.color || BUILDING_CLASS_OPTIONS.suspect.color);
}

function correctionOutlineColor(record) {
  const mode = correctionColorMode();
  if (mode === "ground") return Cesium.Color.fromCssColorString("#7f8a82");
  if (mode === "pale") return Cesium.Color.fromCssColorString("#8b9a92");
  if (mode === "muted") return Cesium.Color.fromCssColorString(CORRECTION_MUTED_COLORS[record?.classId] || "#91aaa0");
  if (mode === "contrast" || mode === "outline") return Cesium.Color.fromCssColorString(CORRECTION_CONTRAST_COLORS[record?.classId] || "#e03131");
  return Cesium.Color.fromCssColorString(record.color || BUILDING_CLASS_OPTIONS.suspect.color);
}

function correctionFillAlpha(lowFeature) {
  const mode = correctionColorMode();
  if (mode === "outline") return lowFeature ? 0.08 : 0.04;
  if (mode === "ground") return lowFeature ? 0.78 : 0.10;
  if (mode === "pale" || mode === "muted") return lowFeature ? 0.82 : 0.14;
  if (mode === "contrast") return lowFeature ? 0.94 : 0.24;
  return lowFeature ? 0.92 : 0.18;
}

function correctionOutlineAlpha() {
  const mode = correctionColorMode();
  if (mode === "ground" || mode === "pale" || mode === "muted") return 0.72;
  return 0.96;
}

function correctionOutlineWidth(lowFeature) {
  const mode = correctionColorMode();
  if (mode === "outline" || mode === "contrast") return lowFeature ? 4 : 5;
  return lowFeature ? 3 : 4;
}

function updateCorrectionSaveControls() {
  const isOriginal = state.correctionVersion === "default";
  const overwriteButton = $("btn-overwrite-class-version");
  const deleteButton = $("btn-delete-class-version");
  if (overwriteButton) {
    overwriteButton.disabled = isOriginal;
    overwriteButton.textContent = isOriginal ? "覆盖当前版本（禁用）" : "覆盖当前版本";
  }
  if (deleteButton) {
    deleteButton.disabled = isOriginal;
    if (isOriginal || state.deleteConfirmVersion !== state.correctionVersion) {
      deleteButton.textContent = isOriginal ? "删除当前版本（禁用）" : "删除当前版本";
      deleteButton.classList.remove("confirming");
    }
  }
  if (isOriginal) {
    state.deleteConfirmVersion = null;
  }
}

function resetDeleteConfirmation() {
  state.deleteConfirmVersion = null;
  const button = $("btn-delete-class-version");
  if (!button) return;
  button.classList.remove("confirming");
  button.textContent = state.correctionVersion === "default" ? "删除当前版本（禁用）" : "删除当前版本";
}

function clearBuildingClassificationOverlays() {
  state.classificationEntities.forEach((entity) => viewer.entities.remove(entity));
  state.classificationEntities = [];
}

function correctionIsLowCityFeature(record) {
  return Boolean(record && record.classId && !FULL_HEIGHT_CITY_FEATURE_CLASSES.has(record.classId));
}

function correctionLowHeight(record) {
  return LOW_CITY_FEATURE_HEIGHT_M[record?.classId] ?? 0.35;
}

function addBuildingClassificationOverlay(item, record) {
  const ring = (item.ring || []).slice();
  if (ring.length < 4) return;
  const closed = ring[0][0] === ring[ring.length - 1][0] && ring[0][1] === ring[ring.length - 1][1];
  const core = closed ? ring.slice(0, -1) : ring;
  if (core.length < 3) return;
  const lowFeature = correctionIsLowCityFeature(record);
  const height = lowFeature ? correctionLowHeight(record) : Math.max(6.0, Number(item.properties?.height_m || 18.0));
  const fillColor = correctionFillColor(record);
  const outlineColor = correctionOutlineColor(record);
  const fillAlpha = correctionFillAlpha(lowFeature);
  const outlineAlpha = correctionOutlineAlpha();
  const roofPositions = Cesium.Cartesian3.fromDegreesArray(core.flatMap(([lon, lat]) => [lon, lat]));
  const closedPositions = [...core, core[0]];
  const roofEntity = viewer.entities.add({
    polygon: {
      hierarchy: new Cesium.PolygonHierarchy(roofPositions),
      height: lowFeature ? height : height + 1.0,
      extrudedHeight: lowFeature ? 0.03 : undefined,
      material: fillColor.withAlpha(fillAlpha),
      outline: true,
      outlineColor: outlineColor.withAlpha(outlineAlpha),
    },
  });
  roofEntity.uavClassificationBuilding = item;
  state.classificationEntities.push(roofEntity);
  const outlineEntity = viewer.entities.add({
    polyline: {
      positions: Cesium.Cartesian3.fromDegreesArrayHeights(
        closedPositions.flatMap(([lon, lat]) => [lon, lat, lowFeature ? height + 0.08 : height + 3.0])
      ),
      width: correctionOutlineWidth(lowFeature),
      material: new Cesium.PolylineGlowMaterialProperty({
        glowPower: 0.18,
        taperPower: 0.35,
        color: outlineColor.withAlpha(outlineAlpha),
      }),
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    },
  });
  outlineEntity.uavClassificationBuilding = item;
  state.classificationEntities.push(outlineEntity);
}

function renderBuildingClassificationOverlays() {
  clearBuildingClassificationOverlays();
  state.buildingIndex.forEach((item) => {
    const record = classRecordFor(item);
    if (record) addBuildingClassificationOverlay(item, record);
  });
  updateBuildingClassEditor();
}

function writeBuildingClassRecord(item, classId, option, note) {
  const props = item.properties || {};
  const key = buildingKey(item);
  state.buildingClassifications[key] = {
    key,
    dataset: currentDatasetKey(),
    classId,
    classLabel: option.label,
    color: option.color,
    note,
    updatedAt: new Date().toISOString(),
    building: {
      osm_id: props.osm_id,
      osm_type: props.osm_type,
      name: props.name || "",
      height_m: props.height_m,
      levels: props.levels || "",
    },
  };
  return key;
}

function applySelectedBuildingClass() {
  const targets = selectedCorrectionTargets();
  if (!targets.length) return;
  const classId = $("building-class-select")?.value || "suspect";
  const option = BUILDING_CLASS_OPTIONS[classId] || BUILDING_CLASS_OPTIONS.suspect;
  const note = $("building-class-note")?.value.trim() || "";
  const keys = targets.map((item) => writeBuildingClassRecord(item, classId, option, note));
  state.correctionDirty = true;
  renderBuildingClassificationOverlays();
  renderMultiSelectionHighlights();
  if (targets.length === 1) {
    showFeatureDetail("建筑属性", {
      ...(targets[0].properties || {}),
      city_feature_correction: state.buildingClassifications[keys[0]],
    });
    return;
  }
  showFeatureDetail("批量城市要素纠错", {
    selected_count: targets.length,
    class_id: classId,
    class_label: option.label,
    updated_keys: keys,
  });
}

function clearSelectedBuildingClass() {
  const targets = selectedCorrectionTargets();
  if (!targets.length) return;
  const keys = targets.map((item) => buildingKey(item));
  keys.forEach((key) => {
    delete state.buildingClassifications[key];
  });
  state.correctionDirty = true;
  renderBuildingClassificationOverlays();
  renderMultiSelectionHighlights();
  if (targets.length === 1) {
    showFeatureDetail("建筑属性", targets[0].properties || {});
    return;
  }
  showFeatureDetail("批量清除城市要素纠错", {
    selected_count: targets.length,
    cleared_keys: keys,
  });
}

async function postCorrectionAction(action, payload) {
  const resp = await fetch("/api/corrections", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, payload }),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || `HTTP ${resp.status}`);
  }
  return resp.json();
}

function markClassEditorTouched() {
  if (selectedCorrectionTargets().length > 0) {
    state.classEditorTouched = true;
  }
}

function confirmOverwriteWithPendingClassEdits() {
  if (
    state.correctionVersion === "default" ||
    !state.classEditorTouched ||
    selectedCorrectionTargets().length === 0
  ) {
    return true;
  }
  const count = selectedCorrectionTargets().length;
  const targetText = count > 1 ? `当前多选的 ${count} 个对象` : "当前选中对象";
  return window.confirm(
    `${targetText}的分类或备注已经修改，但还没有点击“应用纠错”。\n\n`
    + "直接覆盖当前版本不会包含这些未应用的表单改动。\n"
    + "如果要保存这些改动，请先取消，然后点击“应用纠错”。\n\n"
    + "是否继续覆盖当前版本？"
  );
}

async function saveCorrectionVersion(saveMode = "new") {
  try {
    resetDeleteConfirmation();
    if (saveMode === "overwrite" && !confirmOverwriteWithPendingClassEdits()) {
      if ($("class-edit-status")) {
        $("class-edit-status").textContent = "已取消覆盖：请先点击“应用纠错”，再覆盖当前版本。";
      }
      return;
    }
    const payload = {
      ...correctionPayload(),
      saveMode: state.correctionVersion === "default" ? "new" : saveMode,
    };
    const result = await postCorrectionAction("save_version", payload);
    await loadCorrectionVersionIndex(result.version);
    await loadBuildingClassifications();
    state.correctionDirty = false;
    const removed = result.generatedTiles?.removedCount || 0;
    if (removed > 0) {
      await loadWorld();
    } else {
      renderBuildingClassificationOverlays();
    }
    if ($("class-edit-status")) {
      const verb = result.mode === "overwrite" ? "已覆盖" : "已保存";
      const versionLabel = result.label || result.localVersion || result.version;
      $("class-edit-status").textContent = removed > 0
        ? `${verb}${versionLabel}，并生成修正版城市资产；移除 ${removed} 个误识别建筑。`
        : `${verb}${versionLabel}，共 ${result.recordCount} 条。`;
    }
  } catch (error) {
    if ($("class-edit-status")) {
      $("class-edit-status").textContent = `保存失败：${error.message}`;
    }
  }
}

async function setDefaultCorrectionVersion() {
  try {
    if (state.correctionDirty) {
      await saveCorrectionVersion("new");
    }
    const result = await postCorrectionAction("set_default", {
      version: state.correctionVersion,
      datasetKey: currentDatasetKey(),
      cityName: datasetConfig().name || currentDatasetKey(),
      colorMode: correctionColorMode(),
    });
    await loadCorrectionVersionIndex(result.defaultVersion);
    applyDefaultCorrectionColorMode();
    renderBuildingClassificationOverlays();
    if ($("class-edit-status")) {
      const modeLabel = $("building-class-color-mode")?.selectedOptions?.[0]?.textContent || result.defaultColorMode || correctionColorMode();
      $("class-edit-status").textContent = `已设为默认纠错版本：${result.defaultVersion}；默认纠错显示：${modeLabel}。`;
    }
  } catch (error) {
    if ($("class-edit-status")) {
      $("class-edit-status").textContent = `设为默认失败：${error.message}`;
    }
  }
}

async function deleteCurrentCorrectionVersion() {
  const version = state.correctionVersion;
  if (version === "default") {
    if ($("class-edit-status")) {
      $("class-edit-status").textContent = "原始版本禁止删除。";
    }
    updateCorrectionSaveControls();
    return;
  }
  const button = $("btn-delete-class-version");
  if (state.deleteConfirmVersion !== version) {
    state.deleteConfirmVersion = version;
    if (button) {
      button.textContent = "再次确认删除";
      button.classList.add("confirming");
    }
    if ($("class-edit-status")) {
      $("class-edit-status").textContent = `将删除纠错版本 ${version} 及其修正版城市资产；再次点击删除。`;
    }
    return;
  }
  try {
    const result = await postCorrectionAction("delete_version", { version });
    state.deleteConfirmVersion = null;
    await loadCorrectionVersionIndex(result.defaultVersion || "default");
    await loadBuildingClassifications();
    await loadWorld();
    if ($("class-edit-status")) {
      $("class-edit-status").textContent = `已删除纠错版本 ${result.deletedVersion}。`;
    }
  } catch (error) {
    resetDeleteConfirmation();
    if ($("class-edit-status")) {
      $("class-edit-status").textContent = `删除失败：${error.message}`;
    }
  }
}

function clearSelectionHighlight() {
  state.selectionEntities.forEach((entity) => viewer.entities.remove(entity));
  state.selectionEntities = [];
  if (state.selectionEntity) {
    viewer.entities.remove(state.selectionEntity);
    state.selectionEntity = null;
  }
}

function clearMultiSelectionHighlights() {
  state.multiSelectionEntities.forEach((entity) => viewer.entities.remove(entity));
  state.multiSelectionEntities = [];
}

function clearMultiSelection(updateEditor = true) {
  state.multiSelectedBuildings = [];
  clearMultiSelectionHighlights();
  if (updateEditor) updateBuildingClassEditor();
}

function addMultiSelectionHighlight(item, index) {
  const ring = (item.ring || []).slice();
  if (ring.length < 4) return;
  const closed = ring[0][0] === ring[ring.length - 1][0] && ring[0][1] === ring[ring.length - 1][1];
  const core = closed ? ring.slice(0, -1) : ring;
  if (core.length < 3) return;
  const lonCenter = core.reduce((sum, p) => sum + p[0], 0) / core.length;
  const latCenter = core.reduce((sum, p) => sum + p[1], 0) / core.length;
  const scale = 1.04;
  const expanded = core.map(([lon, lat]) => [
    lonCenter + (lon - lonCenter) * scale,
    latCenter + (lat - latCenter) * scale,
  ]);
  const height = Math.max(7.0, Number(item.properties?.height_m || 18.0));
  const color = Cesium.Color.fromCssColorString(index % 2 === 0 ? "#fff2a8" : "#ffd166");
  const positions = Cesium.Cartesian3.fromDegreesArray(expanded.flatMap(([lon, lat]) => [lon, lat]));
  const closedPositions = [...expanded, expanded[0]];
  const fillEntity = viewer.entities.add({
    polygon: {
      hierarchy: new Cesium.PolygonHierarchy(positions),
      height: height + 0.4,
      material: color.withAlpha(0.12),
      outline: true,
      outlineColor: color.withAlpha(0.95),
    },
  });
  fillEntity.uavMultiSelectionBuilding = item;
  state.multiSelectionEntities.push(fillEntity);
  const outlineEntity = viewer.entities.add({
    polyline: {
      positions: Cesium.Cartesian3.fromDegreesArrayHeights(
        closedPositions.flatMap(([lon, lat]) => [lon, lat, height + 7.0])
      ),
      width: 4,
      material: new Cesium.PolylineGlowMaterialProperty({
        glowPower: 0.24,
        taperPower: 0.4,
        color: color.withAlpha(0.98),
      }),
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    },
  });
  outlineEntity.uavMultiSelectionBuilding = item;
  state.multiSelectionEntities.push(outlineEntity);
}

function renderMultiSelectionHighlights() {
  clearMultiSelectionHighlights();
  state.multiSelectedBuildings.forEach((item, index) => addMultiSelectionHighlight(item, index));
}

function toggleBuildingMultiSelection(item) {
  const key = buildingKey(item);
  const index = state.multiSelectedBuildings.findIndex((building) => buildingKey(building) === key);
  state.selectedBuilding = null;
  clearSelectionHighlight();
  if (index >= 0) {
    state.multiSelectedBuildings.splice(index, 1);
  } else {
    state.multiSelectedBuildings.push(item);
  }
  renderMultiSelectionHighlights();
  updateBuildingClassEditor();
  if (state.multiSelectedBuildings.length > 0) {
    showFeatureDetail("批量选择", {
      selected_count: state.multiSelectedBuildings.length,
      operation: "右键或 Ctrl/Command+左键可继续增删多选；应用纠错会批量生效。",
      selected_keys: state.multiSelectedBuildings.map((building) => buildingKey(building)),
    });
  } else {
    $("feature-detail").textContent = "未选中对象。";
  }
}

function setBuildingSelection(item) {
  clearMultiSelection(false);
  state.selectedBuilding = item;
  updateBuildingClassEditor();
  clearSelectionHighlight();
  const ring = (item.ring || []).slice();
  if (ring.length < 4) return;
  const closed = ring[0][0] === ring[ring.length - 1][0] && ring[0][1] === ring[ring.length - 1][1];
  const core = closed ? ring.slice(0, -1) : ring;
  const lonCenter = core.reduce((sum, p) => sum + p[0], 0) / core.length;
  const latCenter = core.reduce((sum, p) => sum + p[1], 0) / core.length;
  const scale = 1.03;
  const expanded = core.map(([lon, lat]) => [
    lonCenter + (lon - lonCenter) * scale,
    latCenter + (lat - latCenter) * scale,
  ]);
  const height = Math.max(8.0, Number(item.properties?.height_m || 18.0));
  const positions = Cesium.Cartesian3.fromDegreesArray(
    expanded.flatMap(([lon, lat]) => [lon, lat])
  );
  const glow = new Cesium.PolylineGlowMaterialProperty({
    glowPower: 0.22,
    taperPower: 0.35,
    color: Cesium.Color.fromCssColorString("#00eaff").withAlpha(0.95),
  });
  state.selectionEntity = viewer.entities.add({
    polygon: {
      hierarchy: new Cesium.PolygonHierarchy(positions),
      height: 0.2,
      extrudedHeight: height + 4.0,
      material: Cesium.Color.fromCssColorString("#00d0ff").withAlpha(0.08),
      outline: true,
      outlineColor: Cesium.Color.fromCssColorString("#00eaff").withAlpha(0.95),
    },
  });
  const expandedClosed = [...expanded, expanded[0]];
  state.selectionEntities.push(viewer.entities.add({
    polyline: {
      positions: Cesium.Cartesian3.fromDegreesArrayHeights(
        expandedClosed.flatMap(([lon, lat]) => [lon, lat, height + 6.0])
      ),
      width: 4,
      material: glow,
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    },
  }));
  const step = expanded.length <= 10 ? 1 : Math.ceil(expanded.length / 10);
  expanded.forEach(([lon, lat], idx) => {
    if (idx % step !== 0) return;
    state.selectionEntities.push(viewer.entities.add({
      polyline: {
        positions: Cesium.Cartesian3.fromDegreesArrayHeights([
          lon, lat, 0.4,
          lon, lat, height + 6.0,
        ]),
        width: 3,
        material: glow,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    }));
  });
}

function weatherSelectionRingPositions(lon, lat, altitude, radiusM) {
  const positions = [];
  const latRadius = radiusM / 111320.0;
  const lonRadius = radiusM / (111320.0 * Math.max(0.2, Math.cos(Cesium.Math.toRadians(lat))));
  for (let idx = 0; idx <= 36; idx += 1) {
    const angle = (Math.PI * 2 * idx) / 36;
    positions.push(
      lon + Math.cos(angle) * lonRadius,
      lat + Math.sin(angle) * latRadius,
      altitude
    );
  }
  return Cesium.Cartesian3.fromDegreesArrayHeights(positions);
}

function setWeatherSelection(feature) {
  clearMultiSelection(false);
  clearSelectionHighlight();
  const props = feature.properties || {};
  const coords = feature.coordinates || [props.lon, props.lat, props.altitude_m];
  const lon = Number(coords[0]);
  const lat = Number(coords[1]);
  const altitude = Number(coords[2] ?? props.altitude_m ?? 100.0);
  if (!Number.isFinite(lon) || !Number.isFinite(lat)) return;
  const safeAltitude = Number.isFinite(altitude) ? altitude : 100.0;
  const glow = new Cesium.PolylineGlowMaterialProperty({
    glowPower: 0.28,
    taperPower: 0.45,
    color: Cesium.Color.fromCssColorString("#fff2a8").withAlpha(0.95),
  });
  state.selectionEntities.push(viewer.entities.add({
    position: Cesium.Cartesian3.fromDegrees(lon, lat, safeAltitude),
    point: {
      pixelSize: 22,
      color: Cesium.Color.fromCssColorString("#00eaff").withAlpha(0.42),
      outlineColor: Cesium.Color.fromCssColorString("#fff2a8"),
      outlineWidth: 4,
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    },
  }));
  state.selectionEntities.push(viewer.entities.add({
    polyline: {
      positions: Cesium.Cartesian3.fromDegreesArrayHeights([
        lon, lat, Math.max(2.0, safeAltitude - 35.0),
        lon, lat, safeAltitude + 35.0,
      ]),
      width: 4,
      material: glow,
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    },
  }));
  state.selectionEntities.push(viewer.entities.add({
    polyline: {
      positions: weatherSelectionRingPositions(lon, lat, safeAltitude, 24.0),
      width: 3,
      material: glow,
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    },
  }));
}

function setRadioSelection(feature) {
  clearMultiSelection(false);
  clearSelectionHighlight();
  const sample = feature.sample || {};
  const lon = Number(sample.lon);
  const lat = Number(sample.lat);
  const altitude = Number(sample.altitude_m || 120.0) + 18.0;
  if (!Number.isFinite(lon) || !Number.isFinite(lat)) return;
  const color = radioCenterDbmColor(sample.pred_center_dbm);
  const glow = new Cesium.PolylineGlowMaterialProperty({
    glowPower: 0.32,
    taperPower: 0.52,
    color: color.withAlpha(0.98),
  });
  state.selectionEntities.push(viewer.entities.add({
    position: Cesium.Cartesian3.fromDegrees(lon, lat, altitude),
    point: {
      pixelSize: 24,
      color: color.withAlpha(0.35),
      outlineColor: Cesium.Color.WHITE.withAlpha(0.95),
      outlineWidth: 4,
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    },
  }));
  state.selectionEntities.push(viewer.entities.add({
    polyline: {
      positions: Cesium.Cartesian3.fromDegreesArrayHeights([
        lon, lat, Math.max(4.0, altitude - 65.0),
        lon, lat, altitude + 65.0,
      ]),
      width: 4,
      material: glow,
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    },
  }));
}

function setRouteSelection(feature) {
  clearMultiSelection(false);
  clearSelectionHighlight();
  const coords = feature.coordinates || [];
  if (coords.length < 2) return;
  const positions = Cesium.Cartesian3.fromDegreesArrayHeights(
    coords.flatMap((coord) => [coord[0], coord[1], coord[2] ?? 100.0])
  );
  const glow = new Cesium.PolylineGlowMaterialProperty({
    glowPower: 0.28,
    taperPower: 0.55,
    color: Cesium.Color.fromCssColorString("#fff2a8").withAlpha(0.98),
  });
  state.selectionEntities.push(viewer.entities.add({
    polyline: {
      positions,
      width: 10,
      material: glow,
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    },
  }));
  [coords[0], coords[coords.length - 1]].forEach((coord, idx) => {
    state.selectionEntities.push(viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(coord[0], coord[1], coord[2] ?? 100.0),
      point: {
        pixelSize: idx === 0 ? 15 : 17,
        color: Cesium.Color.fromCssColorString(idx === 0 ? "#00d0a1" : "#fff2a8").withAlpha(0.92),
        outlineColor: Cesium.Color.fromCssColorString("#10251f"),
        outlineWidth: 3,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    }));
  });
}

function clearRadioProfileOverlay() {
  state.radioProfileEntities.forEach((entity) => viewer.entities.remove(entity));
  state.radioProfileEntities = [];
  state.radioProfileImageryLayers.forEach((layer) => viewer.imageryLayers.remove(layer, true));
  state.radioProfileImageryLayers = [];
  clearRadioPointCloudPrimitive();
  state.radioProfilePointCloudData = null;
  state.radioProfilePointCloudDatasetKey = null;
  state.radioProfile = null;
}

function radioProfileUrl(datasetKey = currentDatasetKey()) {
  return RADIO_PROFILE_URLS[datasetKey] || null;
}

function radioTextureTileUrl(datasetKey = currentDatasetKey()) {
  return RADIO_TEXTURE_TILE_URLS[datasetKey] || null;
}

function radioPointCloudDensityKey() {
  return $("radio-density-select")?.value || "standard";
}

function radioPointCloudSampleFilter() {
  const select = $("radio-sample-filter");
  if (!select) return "all";
  const values = [...select.selectedOptions].map((option) => option.value).filter(Boolean);
  if (!values.length || values.includes("all")) return "all";
  return values.join(",");
}

function radioPointCloudSampleSet() {
  const sampleFilter = radioPointCloudSampleFilter();
  if (sampleFilter === "all") return null;
  return new Set(sampleFilter.split(",").filter(Boolean));
}

function radioPointCloudUrl(datasetKey = currentDatasetKey(), densityKey = radioPointCloudDensityKey()) {
  const config = RADIO_POINT_CLOUD_URLS[datasetKey];
  if (!config) return null;
  if (typeof config === "string") return config;
  return config[densityKey] || config.standard || null;
}

function radioPointCloudDensityInfo(densityKey = radioPointCloudDensityKey()) {
  return RADIO_POINT_CLOUD_DENSITIES[densityKey] || RADIO_POINT_CLOUD_DENSITIES.standard;
}

function savedRadioProfileSetting(datasetKey = currentDatasetKey()) {
  const radioSettings = state.radioProfileSettings || {};
  return radioSettings.datasets?.[datasetKey] || radioSettings.last || {};
}

function applySavedRadioProfileSettings(datasetKey = currentDatasetKey()) {
  const saved = savedRadioProfileSetting(datasetKey);
  const densityKey = RADIO_POINT_CLOUD_DENSITIES[saved.densityKey] ? saved.densityKey : "standard";
  if ($("radio-density-select")) {
    $("radio-density-select").value = densityKey;
  }
  state.radioProfilePendingSampleFilter = saved.sampleFilter || "all";
  if ($("radio-sample-filter")) {
    setRadioSampleFilterSelection(state.radioProfilePendingSampleFilter);
  }
}

async function loadRadioProfileSettings() {
  try {
    const resp = await fetch(WORKBENCH_SETTINGS_API_URL, { cache: "no-store" });
    if (!resp.ok) return;
    const settings = await resp.json();
    state.radioProfileSettings = settings.radioProfile || { last: null, datasets: {} };
    state.radioProfileSettingsLoaded = true;
    applySavedRadioProfileSettings();
  } catch (error) {
    console.warn("无线电画像记忆配置加载失败", error);
  }
}

function rememberCurrentRadioProfileSettings() {
  const datasetKey = currentDatasetKey();
  const current = {
    densityKey: radioPointCloudDensityKey(),
    sampleFilter: radioPointCloudSampleFilter(),
  };
  state.radioProfileSettings.datasets = state.radioProfileSettings.datasets || {};
  state.radioProfileSettings.datasets[datasetKey] = current;
  state.radioProfileSettings.last = { datasetKey, ...current };
  return { datasetKey, ...current };
}

async function saveRadioProfileSettings() {
  if (!state.radioProfileSettingsLoaded) return;
  const payload = rememberCurrentRadioProfileSettings();
  try {
    const resp = await fetch(WORKBENCH_SETTINGS_API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "save_radio_profile", payload }),
    });
    if (!resp.ok) throw new Error(await resp.text());
    const result = await resp.json();
    state.radioProfileSettings = result.radioProfile || state.radioProfileSettings;
  } catch (error) {
    console.warn("无线电画像记忆配置保存失败", error);
  }
}

function updateRadioSampleFilterOptions(samples) {
  const select = $("radio-sample-filter");
  if (!select) return;
  const current = state.radioProfilePendingSampleFilter || radioPointCloudSampleFilter();
  select.innerHTML = '<option value="all">全部采样点</option>';
  samples.forEach((sample, index) => {
    const option = document.createElement("option");
    option.value = sample.sample_id;
    option.textContent = `${String(index + 1).padStart(2, "0")}｜${sample.sample_id.replace(/^.*route_/, "")}`;
    select.appendChild(option);
  });
  setRadioSampleFilterSelection(current);
  state.radioProfilePendingSampleFilter = null;
}

function setRadioSampleFilterSelection(sampleFilter) {
  const select = $("radio-sample-filter");
  if (!select) return;
  const values = new Set(String(sampleFilter || "all").split(",").filter(Boolean));
  if (!values.size) values.add("all");
  let matched = false;
  [...select.options].forEach((option) => {
    option.selected = values.has(option.value);
    matched = matched || option.selected;
  });
  if (!matched && select.options.length) {
    select.options[0].selected = true;
  }
}

function updateRadioDensityNote() {
  const note = $("radio-density-note");
  if (!note) return;
  const pointCloud = state.radioProfilePointCloudData;
  const density = radioPointCloudDensityInfo();
  const sampleSet = radioPointCloudSampleSet();
  const points = Array.isArray(pointCloud?.points)
    ? pointCloud.points.filter((point) => !sampleSet || sampleSet.has(point.sample_id)).length
    : 0;
  const step = Number(pointCloud?.sampling?.grid_step_px);
  const maxPerSample = Number(pointCloud?.sampling?.points_per_sample_max);
  const prefix = Number.isFinite(step) && Number.isFinite(maxPerSample)
    ? `${density.label}点云：每 ${step}px 取 1 点，每采样点最多 ${maxPerSample} 点，约为${density.text}。`
    : `${density.label}点云：约为${density.text}。`;
  const sampleText = sampleSet ? `当前选择 ${sampleSet.size} 个采样点` : "当前显示全部采样点";
  note.textContent = `${prefix}${sampleText}，共 ${points} 个点；按住 Ctrl/Command 可多选。`;
}

function clearRadioPointCloudPrimitive() {
  if (state.radioProfilePointCloud) {
    viewer.scene.primitives.remove(state.radioProfilePointCloud);
    state.radioProfilePointCloud = null;
  }
}

function radioCenterDbmColor(dbm) {
  const value = Number(dbm);
  if (value >= -95) return Cesium.Color.fromCssColorString("#00b894");
  if (value >= -105) return Cesium.Color.fromCssColorString("#f5b342");
  return Cesium.Color.fromCssColorString("#d1495b");
}

function radioHeatPointColor(norm) {
  const value = Math.max(0.0, Math.min(1.0, Number(norm) || 0.0));
  const stops = [
    { t: 0.00, c: Cesium.Color.fromCssColorString("#1f65ff") },
    { t: 0.35, c: Cesium.Color.fromCssColorString("#00c2ff") },
    { t: 0.55, c: Cesium.Color.fromCssColorString("#36d26b") },
    { t: 0.72, c: Cesium.Color.fromCssColorString("#ffd43b") },
    { t: 0.88, c: Cesium.Color.fromCssColorString("#ff7a1a") },
    { t: 1.00, c: Cesium.Color.fromCssColorString("#d7191c") },
  ];
  for (let idx = 1; idx < stops.length; idx += 1) {
    if (value <= stops[idx].t) {
      const prev = stops[idx - 1];
      const next = stops[idx];
      const local = (value - prev.t) / Math.max(1e-6, next.t - prev.t);
      return Cesium.Color.lerp(prev.c, next.c, local, new Cesium.Color());
    }
  }
  return stops[stops.length - 1].c.clone();
}

function radioRecommendationLevel(sample) {
  const centerDbm = Number(sample?.pred_center_dbm ?? -140);
  if (centerDbm >= -95) return "中心较强";
  if (centerDbm >= -105) return "中心可用";
  return "中心偏弱";
}

function updateRadioProfilePanel() {
  const status = $("radio-profile-status");
  const samples = state.radioProfile?.samples || [];
  if (!samples.length) {
    if (status) status.textContent = radioProfileUrl() ? "无线电画像未加载。" : "当前城市没有无线电画像输出。";
    $("radio-stat-samples").textContent = "--";
    $("radio-stat-center").textContent = "--";
    $("radio-stat-score").textContent = "--";
    $("radio-stat-scale").textContent = "--";
    updateRadioSampleFilterOptions([]);
    if ($("radio-density-note")) {
      $("radio-density-note").textContent = "当前城市没有可显示的无线电点云。";
    }
    if ($("radio-profile-note")) {
      $("radio-profile-note").textContent = "彩色采样点按当前位置中心信号强度着色。";
    }
    return;
  }
  const centerValues = samples.map((item) => Number(item.pred_center_dbm)).filter(Number.isFinite);
  const scores = samples.map((item) => Number(item.radio_score)).filter(Number.isFinite);
  const minCenter = Math.min(...centerValues);
  const maxCenter = Math.max(...centerValues);
  const avgScore = scores.reduce((sum, value) => sum + value, 0) / Math.max(1, scores.length);
  const sampling = state.radioProfile?.sampling;
  const pixelSize = Number(sampling?.pixel_size_m);
  const coverageText = Number.isFinite(pixelSize) ? `${Math.round(pixelSize * 256)}m` : "--";
  if (status) {
    status.textContent = `${state.radioProfile.runtime || "GPU"} ${state.radioProfile.framework || "SNPE"} 无线电画像已加载；点击彩色采样点查看中心信号。`;
  }
  $("radio-stat-samples").textContent = String(samples.length);
  $("radio-stat-center").textContent = `${minCenter.toFixed(1)}~${maxCenter.toFixed(1)}`;
  $("radio-stat-score").textContent = avgScore.toFixed(0);
  $("radio-stat-scale").textContent = coverageText;
  updateRadioSampleFilterOptions(samples);
  updateRadioDensityNote();
  if ($("radio-profile-note")) {
    const filter = state.radioProfile?.building_height_filter;
    const filterText = filter?.mode === "uav_altitude_slice"
      ? "当前画像采用无人机高度切片：低于无人机当前高度的建筑不进入阻挡栅格。"
      : "当前画像未声明建筑高度切片规则。";
    const roadPolicy = state.radioProfile?.road_channel_policy;
    const roadText = roadPolicy?.mode === "merge_to_other"
      ? "地面道路已合并到其他地物，避免被模型误判为高空链路阻挡。"
      : roadPolicy?.mode === "keep"
        ? "当前画像保留独立道路通道。"
        : "当前画像未声明道路通道策略。";
    const scaleText = Number.isFinite(pixelSize)
      ? `当前局部热力图默认尺度为 ${pixelSize.toFixed(1)}m/px，覆盖约 ${Math.round(pixelSize * 256)}m × ${Math.round(pixelSize * 256)}m。`
      : "";
    $("radio-profile-note").textContent = `彩色采样点按当前位置中心信号强度着色；热力图贴片直接来自模型输出预测矩阵，红色较强、蓝色较弱。${scaleText}${filterText}${roadText}`;
  }
}

function radioSampleFeature(sample) {
  return {
    type: "radio",
    label: "无线电画像采样点",
    properties: {
      sample_id: sample.sample_id,
      lon: sample.lon,
      lat: sample.lat,
      altitude_m: sample.altitude_m,
      distance_along_route_m: sample.distance_along_route_m,
      pred_center_dbm: sample.pred_center_dbm,
      pred_mean_dbm: sample.pred_mean_dbm,
      pred_min_dbm: sample.pred_min_dbm,
      pred_max_dbm: sample.pred_max_dbm,
      coverage_ratio_gt_minus90: sample.coverage_ratio_gt_minus90,
      weak_ratio_lt_minus100: sample.weak_ratio_lt_minus100,
      radio_score: sample.radio_score,
      recommendation: sample.recommendation,
    },
    sample,
  };
}

function addRadioTextureTile(tile, baseUrl) {
  const bbox = tile?.window_bbox;
  if (!bbox || !tile.image) return;
  const west = Number(bbox.west);
  const south = Number(bbox.south);
  const east = Number(bbox.east);
  const north = Number(bbox.north);
  if (![west, south, east, north].every(Number.isFinite)) return;
  const imageUrl = assetUrl(`${baseUrl}${tile.image}`);
  const provider = new Cesium.SingleTileImageryProvider({
    url: imageUrl,
    rectangle: Cesium.Rectangle.fromDegrees(west, south, east, north),
  });
  const layer = viewer.imageryLayers.addImageryProvider(provider);
  layer.alpha = 0.92;
  layer.brightness = 1.03;
  state.radioProfileImageryLayers.push(layer);
}

async function loadRadioTextureTiles(datasetKey = currentDatasetKey()) {
  const url = radioTextureTileUrl(datasetKey);
  if (!url) return null;
  try {
    const resp = await fetch(assetUrl(url), { cache: "no-store" });
    if (!resp.ok) return null;
    return await resp.json();
  } catch (error) {
    console.warn("无线电热力贴图加载失败", error);
    return null;
  }
}

async function loadRadioPointCloud(datasetKey = currentDatasetKey(), densityKey = radioPointCloudDensityKey()) {
  const url = radioPointCloudUrl(datasetKey, densityKey);
  if (!url) return null;
  try {
    const resp = await fetch(assetUrl(url), { cache: "no-store" });
    if (!resp.ok) return null;
    return await resp.json();
  } catch (error) {
    console.warn("无线电热力点云加载失败", error);
    return null;
  }
}

function renderRadioPointCloud(pointCloud) {
  if (pointCloud?.schema !== "uav_route_radio_point_cloud_v1" || !Array.isArray(pointCloud.points)) {
    clearRadioPointCloudPrimitive();
    updateRadioDensityNote();
    return;
  }
  let collection = state.radioProfilePointCloud;
  if (collection) {
    collection.removeAll();
  } else {
    collection = viewer.scene.primitives.add(new Cesium.PointPrimitiveCollection());
    state.radioProfilePointCloud = collection;
  }
  const sampleSet = radioPointCloudSampleSet();
  const density = radioPointCloudDensityInfo();
  pointCloud.points.forEach((point) => {
    if (sampleSet && !sampleSet.has(point.sample_id)) return;
    const lon = Number(point.lon);
    const lat = Number(point.lat);
    const altitude = Number(point.altitude_m);
    if (![lon, lat, altitude].every(Number.isFinite)) return;
    const norm = Math.max(0.0, Math.min(1.0, Number(point.norm) || 0.0));
    const color = radioHeatPointColor(norm);
    collection.add({
      position: Cesium.Cartesian3.fromDegrees(lon, lat, altitude),
      pixelSize: density.baseSize + norm * density.gainSize,
      color: color.withAlpha(0.20 + norm * 0.56),
      outlineColor: Cesium.Color.WHITE.withAlpha(0.06),
      outlineWidth: 0,
      id: {
        uavFeature: {
          type: "radio_heat",
          label: "无线电热力点",
          properties: {
            sample_id: point.sample_id,
            dbm: point.dbm,
            norm: point.norm,
            lon: point.lon,
            lat: point.lat,
            altitude_m: point.altitude_m,
          },
        },
      },
    });
  });
  updateRadioDensityNote();
}

function rerenderRadioPointCloud() {
  if (state.radioProfilePointCloudData) {
    renderRadioPointCloud(state.radioProfilePointCloudData);
  } else {
    updateRadioDensityNote();
  }
}

async function reloadRadioPointCloudForControls() {
  const datasetKey = currentDatasetKey();
  clearRadioPointCloudPrimitive();
  const pointCloud = await loadRadioPointCloud(datasetKey);
  state.radioProfilePointCloudData = pointCloud;
  state.radioProfilePointCloudDatasetKey = datasetKey;
  rerenderRadioPointCloud();
}

function renderRadioProfileOverlay(profile, textureTiles = null, pointCloud = null) {
  clearRadioProfileOverlay();
  if (!profile || profile.schema !== "uav_route_radio_profile_v1" || !Array.isArray(profile.samples) || profile.samples.length < 2) {
    updateRadioProfilePanel();
    return;
  }
  state.radioProfile = profile;
  const samples = profile.samples;
  updateRadioSampleFilterOptions(samples);
  if (pointCloud?.schema === "uav_route_radio_point_cloud_v1") {
    state.radioProfilePointCloudData = pointCloud;
    state.radioProfilePointCloudDatasetKey = currentDatasetKey();
    renderRadioPointCloud(pointCloud);
  } else if (textureTiles?.schema === "uav_route_radio_texture_tiles_v1" && Array.isArray(textureTiles.items) && viewer.scene.globe?.show) {
    const baseUrl = "../outputs/radio_route_inputs/manhattan_midtown_scale_2p5m/";
    textureTiles.items.forEach((tile) => addRadioTextureTile(tile, baseUrl));
  }
  for (let idx = 1; idx < samples.length; idx += 1) {
    const prev = samples[idx - 1];
    const current = samples[idx];
    const centerDbm = (Number(prev.pred_center_dbm || -140) + Number(current.pred_center_dbm || -140)) / 2.0;
    const color = radioCenterDbmColor(centerDbm);
    state.radioProfileEntities.push(viewer.entities.add({
      polyline: {
        positions: Cesium.Cartesian3.fromDegreesArrayHeights([
          Number(prev.lon), Number(prev.lat), Number(prev.altitude_m || 120) + 10.0,
          Number(current.lon), Number(current.lat), Number(current.altitude_m || 120) + 10.0,
        ]),
        width: 9,
        material: new Cesium.PolylineGlowMaterialProperty({
          glowPower: 0.18,
          taperPower: 0.42,
          color: color.withAlpha(0.96),
        }),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    }));
  }
  samples.forEach((sample) => {
    const color = radioCenterDbmColor(sample.pred_center_dbm);
    const feature = radioSampleFeature(sample);
    const entity = viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(Number(sample.lon), Number(sample.lat), Number(sample.altitude_m || 120) + 16.0),
      point: {
        pixelSize: 12,
        color: color.withAlpha(0.92),
        outlineColor: Cesium.Color.fromCssColorString("#10251f"),
        outlineWidth: 2,
        scaleByDistance: new Cesium.NearFarScalar(300.0, 1.0, 4500.0, 0.22),
        translucencyByDistance: new Cesium.NearFarScalar(800.0, 1.0, 6500.0, 0.30),
        disableDepthTestDistance: 3500.0,
      },
      label: {
        text: `${Number(sample.pred_center_dbm || 0).toFixed(0)} dBm`,
        font: "800 10px Avenir Next, sans-serif",
        fillColor: Cesium.Color.fromCssColorString("#10251f"),
        outlineColor: Cesium.Color.WHITE.withAlpha(0.86),
        outlineWidth: 2,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        pixelOffset: new Cesium.Cartesian2(0, -21),
        scaleByDistance: new Cesium.NearFarScalar(300.0, 1.0, 4500.0, 0.18),
        translucencyByDistance: new Cesium.NearFarScalar(800.0, 1.0, 6500.0, 0.0),
        disableDepthTestDistance: 3500.0,
      },
    });
    entity.uavFeature = feature;
    state.radioProfileEntities.push(entity);
  });
  updateRadioProfilePanel();
}

async function loadRadioProfileForDataset(datasetKey = currentDatasetKey()) {
  applySavedRadioProfileSettings(datasetKey);
  clearRadioProfileOverlay();
  const url = radioProfileUrl(datasetKey);
  if (!url) {
    updateRadioProfilePanel();
    return;
  }
  try {
    const resp = await fetch(assetUrl(url), { cache: "no-store" });
    if (!resp.ok) {
      updateRadioProfilePanel();
      return;
    }
    const profile = await resp.json();
    const textureTiles = await loadRadioTextureTiles(datasetKey);
    const pointCloud = await loadRadioPointCloud(datasetKey);
    renderRadioProfileOverlay(profile, textureTiles, pointCloud);
  } catch (error) {
    console.warn("无线电画像加载失败", error);
    updateRadioProfilePanel();
  }
}

function routeDraftAltitude() {
  const value = Number($("route-draw-altitude")?.value || 120);
  return Math.max(20.0, Math.min(800.0, Number.isFinite(value) ? value : 120.0));
}

function routeDraftSpeed() {
  const value = Number($("route-draw-speed")?.value || 8);
  return Math.max(0.5, Math.min(40.0, Number.isFinite(value) ? value : 8.0));
}

function routeDraftName() {
  const value = String($("route-draw-name")?.value || "").trim();
  return value || "用户绘制航线";
}

function routeDraftCoordinates(includePreview = true) {
  const coords = state.routeDraft.points.slice();
  if (includePreview && state.routeDraft.drawing && state.routeDraft.preview && coords.length > 0) {
    coords.push(state.routeDraft.preview);
  }
  return coords;
}

function routeDraftPositions(includePreview = true, ground = false) {
  const coords = routeDraftCoordinates(includePreview);
  if (coords.length < 2) return [];
  return Cesium.Cartesian3.fromDegreesArrayHeights(
    coords.flatMap((coord) => [coord[0], coord[1], ground ? 2.0 : coord[2]])
  );
}

function routeDraftLengthM(points = state.routeDraft.points) {
  if (points.length < 2) return 0.0;
  const positions = points.map((coord) => Cesium.Cartesian3.fromDegrees(coord[0], coord[1], coord[2]));
  let total = 0.0;
  for (let idx = 1; idx < positions.length; idx += 1) {
    total += Cesium.Cartesian3.distance(positions[idx - 1], positions[idx]);
  }
  return total;
}

function routeDraftSegmentIntersects(a, b, c, d) {
  const orient = (p, q, r) => (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]);
  const onSegment = (p, q, r) => (
    Math.min(p[0], q[0]) <= r[0] && r[0] <= Math.max(p[0], q[0]) &&
    Math.min(p[1], q[1]) <= r[1] && r[1] <= Math.max(p[1], q[1]) &&
    Math.abs(orient(p, q, r)) < 1e-12
  );
  const o1 = orient(a, b, c);
  const o2 = orient(a, b, d);
  const o3 = orient(c, d, a);
  const o4 = orient(c, d, b);
  if (o1 * o2 < 0 && o3 * o4 < 0) return true;
  return onSegment(a, b, c) || onSegment(a, b, d) || onSegment(c, d, a) || onSegment(c, d, b);
}

function routeDraftHitsBuilding(a, b, building) {
  const ring = building.ring || [];
  if (ring.length < 4) return false;
  const minLon = Math.min(a[0], b[0]);
  const maxLon = Math.max(a[0], b[0]);
  const minLat = Math.min(a[1], b[1]);
  const maxLat = Math.max(a[1], b[1]);
  const bounds = building.bounds || ringBounds(ring);
  if (maxLon < bounds.west || minLon > bounds.east || maxLat < bounds.south || minLat > bounds.north) return false;
  const height = Number(building.properties?.height_m || 0);
  if (Math.min(a[2], b[2]) > height + 20.0) return false;
  if (pointInRing(a[0], a[1], ring) || pointInRing(b[0], b[1], ring)) return true;
  for (let idx = 0; idx < ring.length - 1; idx += 1) {
    if (routeDraftSegmentIntersects(a, b, ring[idx], ring[idx + 1])) return true;
  }
  return false;
}

function routeDraftWarnings() {
  const points = state.routeDraft.points;
  const warnings = [];
  if (points.length < 2) {
    warnings.push("至少需要 2 个航点。");
    return warnings;
  }
  let buildingHits = 0;
  for (let idx = 1; idx < points.length; idx += 1) {
    const a = points[idx - 1];
    const b = points[idx];
    if (state.buildingIndex.some((building) => routeDraftHitsBuilding(a, b, building))) {
      buildingHits += 1;
    }
  }
  if (buildingHits > 0) {
    warnings.push(`${buildingHits} 段航线可能穿越建筑 footprint 或安全余量不足。`);
  }
  return warnings;
}

function clearRouteDraftEntities() {
  [state.routeDraft.lineEntity, state.routeDraft.groundEntity, ...state.routeDraft.pointEntities]
    .filter(Boolean)
    .forEach((entity) => viewer.entities.remove(entity));
  state.routeDraft.lineEntity = null;
  state.routeDraft.groundEntity = null;
  state.routeDraft.pointEntities = [];
}

function resetRouteDraft(clearPoints = true) {
  clearRouteDraftEntities();
  state.routeDraft.drawing = false;
  state.routeDraft.preview = null;
  state.routeDraft.dirty = false;
  state.routeDraft.savedVersion = null;
  if (clearPoints) state.routeDraft.points = [];
  syncRouteDraftUI();
}

function ensureRouteDraftLineEntities() {
  if (!state.routeDraft.lineEntity) {
    state.routeDraft.lineEntity = viewer.entities.add({
      polyline: {
        positions: new Cesium.CallbackProperty(() => routeDraftPositions(true, false), false),
        width: 6,
        material: new Cesium.PolylineGlowMaterialProperty({
          glowPower: 0.22,
          taperPower: 0.42,
          color: Cesium.Color.fromCssColorString("#00d0a1").withAlpha(0.96),
        }),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    });
  }
  if (!state.routeDraft.groundEntity) {
    state.routeDraft.groundEntity = viewer.entities.add({
      polyline: {
        positions: new Cesium.CallbackProperty(() => routeDraftPositions(true, true), false),
        width: 3,
        material: new Cesium.PolylineDashMaterialProperty({
          color: Cesium.Color.fromCssColorString("#10251f").withAlpha(0.68),
          dashLength: 14.0,
        }),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    });
  }
}

function syncRouteDraftMarkers() {
  state.routeDraft.pointEntities.forEach((entity) => viewer.entities.remove(entity));
  state.routeDraft.pointEntities = [];
  state.routeDraft.points.forEach((coord, idx) => {
    const color = idx === 0
      ? Cesium.Color.fromCssColorString("#00d0a1")
      : idx === state.routeDraft.points.length - 1
        ? Cesium.Color.fromCssColorString("#f5b342")
        : Cesium.Color.fromCssColorString("#fff2a8");
    state.routeDraft.pointEntities.push(viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(coord[0], coord[1], coord[2]),
      point: {
        pixelSize: idx === 0 || idx === state.routeDraft.points.length - 1 ? 16 : 12,
        color: color.withAlpha(0.95),
        outlineColor: Cesium.Color.fromCssColorString("#10251f"),
        outlineWidth: 3,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      label: {
        text: `${idx + 1}`,
        font: "800 12px Avenir Next, sans-serif",
        fillColor: Cesium.Color.fromCssColorString("#10251f"),
        outlineColor: Cesium.Color.WHITE.withAlpha(0.85),
        outlineWidth: 3,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        pixelOffset: new Cesium.Cartesian2(0, -22),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    }));
  });
}

function syncRouteDraftUI() {
  const panel = document.querySelector(".route-draw-panel");
  panel?.classList.toggle("active", state.routeDraft.drawing);
  const points = state.routeDraft.points;
  const lengthM = routeDraftLengthM(points);
  const minutes = lengthM > 0 ? lengthM / routeDraftSpeed() / 60.0 : 0.0;
  const warnings = routeDraftWarnings();
  $("route-draw-stats").textContent = [
    `航点 ${points.length}`,
    `距离 ${(lengthM / 1000.0).toFixed(2)} km`,
    `预计 ${minutes.toFixed(1)} min`,
    warnings.length ? `校验 ${warnings.join(" ")}` : "校验通过",
  ].join("｜");
  const list = $("route-waypoint-list");
  list.innerHTML = "";
  points.forEach((coord, idx) => {
    const item = document.createElement("li");
    item.textContent = `${idx + 1}. ${coord[0].toFixed(6)}, ${coord[1].toFixed(6)}, ${Math.round(coord[2])}m`;
    list.appendChild(item);
  });
  $("btn-route-draw-start").textContent = state.routeDraft.drawing ? "绘制中" : (points.length ? "继续绘制" : "开始绘制");
  $("btn-route-draw-start").disabled = state.routeDraft.drawing;
  $("btn-route-draw-finish").disabled = !state.routeDraft.drawing;
  $("btn-route-draw-undo").disabled = points.length === 0;
  $("btn-route-draw-clear").disabled = points.length === 0 && !state.routeDraft.drawing;
  $("btn-route-draw-save").disabled = points.length < 2;
}

function setRouteDrawStatus(message) {
  const status = $("route-draw-status");
  if (status) status.textContent = message;
}

function startRouteDrawing() {
  if (!state.center) {
    setRouteDrawStatus("请先加载城市世界，再开始绘制航线。");
    return;
  }
  clearMultiSelection(false);
  clearSelectionHighlight();
  state.routeDraft.drawing = true;
  state.routeDraft.preview = null;
  state.routeDraft.dirty = true;
  ensureRouteDraftLineEntities();
  setRouteDrawStatus("绘制中：左键单击添加航点；拖动旋转视角；点击“完成绘制”结束。");
  syncRouteDraftUI();
}

function addRouteDraftWaypointFromPosition(position) {
  const location = screenToLonLat(position);
  if (!location) {
    setRouteDrawStatus("无法定位点击位置，请调整视角后重试。");
    return;
  }
  ensureRouteDraftLineEntities();
  const point = [
    Number(location.lon.toFixed(7)),
    Number(location.lat.toFixed(7)),
    routeDraftAltitude(),
  ];
  state.routeDraft.points.push(point);
  state.routeDraft.preview = null;
  state.routeDraft.dirty = true;
  state.routeDraft.savedVersion = null;
  syncRouteDraftMarkers();
  syncRouteDraftUI();
  showFeatureDetail("绘制航点", {
    index: state.routeDraft.points.length,
    lon: point[0],
    lat: point[1],
    altitude_m: point[2],
    altitude_mode: $("route-draw-altitude-mode")?.value || "relative_ground",
  });
  setRouteDrawStatus(`已添加航点 ${state.routeDraft.points.length}。`);
}

function updateRouteDraftPreview(clientX, clientY) {
  if (!state.routeDraft.drawing || state.routeDraft.points.length === 0) return;
  const rect = interactionTarget.getBoundingClientRect();
  if (clientX < rect.left || clientX > rect.right || clientY < rect.top || clientY > rect.bottom) return;
  const location = screenToLonLat(new Cesium.Cartesian2(clientX - rect.left, clientY - rect.top));
  if (!location) return;
  state.routeDraft.preview = [
    Number(location.lon.toFixed(7)),
    Number(location.lat.toFixed(7)),
    routeDraftAltitude(),
  ];
}

function finishRouteDrawing() {
  if (state.routeDraft.points.length < 2) {
    setRouteDrawStatus("至少添加 2 个航点后才能完成绘制。");
    return;
  }
  state.routeDraft.drawing = false;
  state.routeDraft.preview = null;
  const warnings = routeDraftWarnings();
  const feature = routeDraftFeature();
  setRouteSelection(feature);
  showFeatureDetail("绘制航线", feature.properties);
  setRouteDrawStatus(warnings.length ? `已完成，存在风险：${warnings.join(" ")}` : "已完成，基础校验通过。");
  syncRouteDraftUI();
}

function undoRouteDraftWaypoint() {
  if (state.routeDraft.points.length === 0) return;
  state.routeDraft.points.pop();
  state.routeDraft.preview = null;
  state.routeDraft.dirty = true;
  state.routeDraft.savedVersion = null;
  syncRouteDraftMarkers();
  syncRouteDraftUI();
  setRouteDrawStatus("已撤销上一航点。");
}

function clearRouteDraft() {
  resetRouteDraft(true);
  setRouteDrawStatus("已清空绘制航线。");
}

function routeDraftFeature() {
  const points = state.routeDraft.points;
  const lengthM = routeDraftLengthM(points);
  return {
    type: "route",
    label: "绘制航线",
    properties: {
      layer: "user_drawn_route",
      route_name: routeDraftName(),
      city: datasetConfig().name || currentDatasetKey(),
      datasetKey: currentDatasetKey(),
      waypoint_count: points.length,
      route_length_m: Number(lengthM.toFixed(2)),
      route_length_km: Number((lengthM / 1000.0).toFixed(3)),
      altitude_mode: $("route-draw-altitude-mode")?.value || "relative_ground",
      default_speed_mps: routeDraftSpeed(),
      warnings: routeDraftWarnings(),
    },
    coordinates: points,
  };
}

async function saveRouteDraft() {
  if (state.routeDraft.points.length < 2) {
    setRouteDrawStatus("至少需要 2 个航点才能保存。");
    return;
  }
  const payload = {
    datasetKey: currentDatasetKey(),
    cityName: datasetConfig().name || currentDatasetKey(),
    routeName: routeDraftName(),
    altitudeMode: $("route-draw-altitude-mode")?.value || "relative_ground",
    defaultSpeedMps: routeDraftSpeed(),
    coordinates: state.routeDraft.points,
  };
  const resp = await fetch(ROUTE_DRAFT_API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "save_route", payload }),
  });
  if (!resp.ok) {
    throw new Error(await resp.text());
  }
  const result = await resp.json();
  state.routeDraft.savedVersion = result.version;
  state.routeDraft.dirty = false;
  setRouteDrawStatus(`已保存航线草稿：${result.localVersion}，路径 outputs/route_drafts/${result.path}`);
  syncRouteDraftUI();
}

function ringBounds(ring) {
  const lons = ring.map((coord) => coord[0]);
  const lats = ring.map((coord) => coord[1]);
  return {
    west: Math.min(...lons),
    east: Math.max(...lons),
    south: Math.min(...lats),
    north: Math.max(...lats),
  };
}

function ringArea(ring) {
  let area = 0;
  for (let idx = 0; idx < ring.length - 1; idx += 1) {
    area += ring[idx][0] * ring[idx + 1][1] - ring[idx + 1][0] * ring[idx][1];
  }
  return Math.abs(area) / 2;
}

function pointInRing(lon, lat, ring) {
  let inside = false;
  for (let idx = 0; idx < ring.length - 1; idx += 1) {
    const [x1, y1] = ring[idx];
    const [x2, y2] = ring[idx + 1];
    if ((y1 > lat) !== (y2 > lat)) {
      const crossLon = ((x2 - x1) * (lat - y1)) / (y2 - y1 + 1e-30) + x1;
      if (lon < crossLon) inside = !inside;
    }
  }
  return inside;
}

function findBuildingAt(lon, lat) {
  const matches = state.buildingIndex.filter((item) => (
    lon >= item.bounds.west &&
    lon <= item.bounds.east &&
    lat >= item.bounds.south &&
    lat <= item.bounds.north &&
    pointInRing(lon, lat, item.ring)
  ));
  matches.sort((a, b) => {
    const heightDelta = Number(b.properties.height_m || 0) - Number(a.properties.height_m || 0);
    if (Math.abs(heightDelta) > 0.001) return heightDelta;
    return a.area - b.area;
  });
  return matches[0] || null;
}

async function loadBuildingIndex(url) {
  state.buildingIndex = [];
  const resp = await fetch(url, { cache: "no-store" });
  if (!resp.ok) return;
  const geo = await resp.json();
  state.buildingIndex = (geo.features || [])
    .filter((feature) => feature.geometry?.type === "Polygon" && feature.geometry.coordinates?.[0]?.length >= 4)
    .map((feature) => {
      const ring = feature.geometry.coordinates[0];
      return {
        properties: feature.properties || {},
        ring,
        bounds: ringBounds(ring),
        area: ringArea(ring),
      };
    });
}

function screenToLonLat(position) {
  let cartesian = null;
  if (viewer.scene.pickPositionSupported) {
    try {
      cartesian = viewer.scene.pickPosition(position);
    } catch (error) {
      cartesian = null;
    }
  }
  if (!Cesium.defined(cartesian)) {
    cartesian = viewer.camera.pickEllipsoid(position, Cesium.Ellipsoid.WGS84);
  }
  if (!Cesium.defined(cartesian)) return null;
  const cartographic = Cesium.Cartographic.fromCartesian(cartesian);
  return {
    lon: Cesium.Math.toDegrees(cartographic.longitude),
    lat: Cesium.Math.toDegrees(cartographic.latitude),
    height_m: Math.round(cartographic.height * 10) / 10,
  };
}

function pickedObjectId(picked) {
  return picked?.id || picked?.primitive?.id || null;
}

function nearestWeatherFeatureAt(position, maxDistancePx = 18.0) {
  let best = null;
  let bestDistance = Number.POSITIVE_INFINITY;
  for (const feature of state.weatherFeatures || []) {
    if (!weatherFeatureVisible(feature)) continue;
    const coords = feature.geometry?.coordinates || [];
    const altitude = Number(coords[2] ?? feature.properties?.altitude_m ?? 100.0);
    const world = Cesium.Cartesian3.fromDegrees(Number(coords[0]), Number(coords[1]), Number.isFinite(altitude) ? altitude : 100.0);
    const screen = Cesium.SceneTransforms.worldToWindowCoordinates(viewer.scene, world);
    if (!screen) continue;
    const distance = Math.hypot(screen.x - position.x, screen.y - position.y);
    if (distance < bestDistance) {
      bestDistance = distance;
      best = createWeatherPrimitive(feature).id.uavFeature;
    }
  }
  return bestDistance <= maxDistancePx ? best : null;
}

function handleSceneClick(clientX, clientY, options = {}) {
  const rect = interactionTarget.getBoundingClientRect();
  if (clientX < rect.left || clientX > rect.right || clientY < rect.top || clientY > rect.bottom) return;
  const position = new Cesium.Cartesian2(clientX - rect.left, clientY - rect.top);
  if (state.routeDraft.drawing) {
    addRouteDraftWaypointFromPosition(position);
    return;
  }
  const picked = viewer.scene.pick(position);
  const pickedId = pickedObjectId(picked);
  if (pickedId?.uavClassificationBuilding) {
    const building = pickedId.uavClassificationBuilding;
    if (options.multi) {
      toggleBuildingMultiSelection(building);
      return;
    }
    setBuildingSelection(building);
    showFeatureDetail("建筑属性", {
      ...(building.properties || {}),
      city_feature_correction: classRecordFor(building) || null,
    });
    return;
  }
  if (pickedId?.uavMultiSelectionBuilding) {
    const building = pickedId.uavMultiSelectionBuilding;
    if (options.multi) {
      toggleBuildingMultiSelection(building);
      return;
    }
    setBuildingSelection(building);
    showFeatureDetail("建筑属性", {
      ...(building.properties || {}),
      city_feature_correction: classRecordFor(building) || null,
    });
    return;
  }
  if (pickedId?.uavFeature) {
    clearMultiSelection(false);
    state.selectedBuilding = null;
    updateBuildingClassEditor();
    if (pickedId.uavFeature.type === "weather") {
      setWeatherSelection(pickedId.uavFeature);
    } else if (pickedId.uavFeature.type === "radio") {
      setRadioSelection(pickedId.uavFeature);
    } else if (pickedId.uavFeature.type === "route") {
      setRouteSelection(pickedId.uavFeature);
    } else {
      clearSelectionHighlight();
    }
    showFeatureDetail(pickedId.uavFeature.label, pickedId.uavFeature.properties);
    return;
  }
  const nearbyWeather = nearestWeatherFeatureAt(position);
  if (nearbyWeather) {
    clearMultiSelection(false);
    state.selectedBuilding = null;
    updateBuildingClassEditor();
    setWeatherSelection(nearbyWeather);
    showFeatureDetail(nearbyWeather.label, nearbyWeather.properties);
    return;
  }
  const location = screenToLonLat(position);
  if (!location) {
    if (options.multi) return;
    clearMultiSelection(false);
    state.selectedBuilding = null;
    updateBuildingClassEditor();
    clearSelectionHighlight();
    $("feature-detail").textContent = "未选中对象。";
    return;
  }
  const building = findBuildingAt(location.lon, location.lat);
  if (building) {
    if (options.multi) {
      toggleBuildingMultiSelection(building);
      return;
    }
    setBuildingSelection(building);
    const manualClass = classRecordFor(building);
    showFeatureDetail("建筑属性", {
      ...building.properties,
      city_feature_correction: manualClass || null,
      click_lon: Number(location.lon.toFixed(7)),
      click_lat: Number(location.lat.toFixed(7)),
      click_height_m: location.height_m,
    });
    return;
  }
  if (options.multi) return;
  clearMultiSelection(false);
  clearSelectionHighlight();
  state.selectedBuilding = null;
  updateBuildingClassEditor();
  showFeatureDetail("空间位置", {
    lon: Number(location.lon.toFixed(7)),
    lat: Number(location.lat.toFixed(7)),
    height_m: location.height_m,
  });
}

function buildingColor(entity, height, risk) {
  const mode = buildingRenderMode();
  if (mode === "height") {
    return heightColor(height);
  }
  if (mode === "risk") {
    return riskColor(risk);
  }
  if (height >= 160) return Cesium.Color.fromCssColorString("#8f7662");
  if (height >= 100) return Cesium.Color.fromCssColorString("#a99884");
  if (height >= 60) return Cesium.Color.fromCssColorString("#b8b1a4");
  return Cesium.Color.fromCssColorString("#c6cbc4");
}

function restyleBuildings() {
  state.buildingEntities.forEach((entity) => {
    if (!entity.polygon) return;
    const height = Number(entity.properties.height_m?.getValue?.() || 0);
    const levels = Number(entity.properties.levels?.getValue?.() || 0);
    const risk = Number(entity.properties.risk_score_add?.getValue?.() || 0);
    const base = buildingColor(entity, height, risk);
    const finalAlpha = Math.min(0.96, 0.68 + Math.min(height, 220) / 500.0 + levels * 0.01);
    entity.polygon.material = base.withAlpha(finalAlpha);
  });
}

function styleEntity(entity) {
  const layer = entityLayer(entity);
  if (layer === "building" || layer === "real_building") {
    if (!entity.polygon) return;
    if (entity.polygon) {
      const height = Number(entity.properties.height_m.getValue() || 0);
      const levels = Number(entity.properties.levels?.getValue?.() || 0);
      const source = String(entity.properties.source?.getValue?.() || "");
      const isNamed = Boolean(entity.properties.name?.getValue?.());
      const risk = Number(entity.properties.risk_score_add?.getValue?.() || 0);
      const base = buildingColor(entity, height, risk);
      const alpha = source === "openstreetmap" ? 0.88 : 0.76;
      const material = base.withAlpha(alpha);
      entity.polygon.height = new Cesium.ConstantProperty(0.0);
      entity.polygon.extrudedHeight = undefined;
      entity.polygon.material = material;
      entity.polygon.outline = true;
      entity.polygon.outlineColor = isNamed
        ? Cesium.Color.fromCssColorString("#fff2d6").withAlpha(0.44)
        : Cesium.Color.fromCssColorString("#e8efe8").withAlpha(0.24);
      entity.polygon.distanceDisplayCondition = new Cesium.DistanceDisplayCondition(0.0, 14000.0);
      const finalAlpha = Math.min(0.96, 0.68 + Math.min(height, 220) / 500.0 + levels * 0.01);
      entity.polygon.material = base.withAlpha(finalAlpha);
      if (height >= 120 && isNamed) {
        entity.label = new Cesium.LabelGraphics({
          text: String(entity.properties.name.getValue()),
          font: "600 13px Avenir Next, sans-serif",
          fillColor: Cesium.Color.fromCssColorString("#fff6df"),
          outlineColor: Cesium.Color.fromCssColorString("#1b241f"),
          outlineWidth: 3,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          pixelOffset: new Cesium.Cartesian2(0, -10),
          distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0.0, 4200.0),
          disableDepthTestDistance: 5000.0,
        });
      }
      state.buildingEntities.push(entity);
    }
  }
  if (layer === "ground") {
    if (!entity.polygon) return;
    entity.polygon.material = Cesium.Color.fromCssColorString("#e5eadf").withAlpha(0.42);
    entity.polygon.outline = true;
    entity.polygon.outlineColor = Cesium.Color.fromCssColorString("#c7d6c8").withAlpha(0.22);
    state.groundEntities.push(entity);
  }
  if (layer === "road") {
    entity.polyline.width = Number(entity.properties.width_px?.getValue?.() || 2);
    const width = Number(entity.properties.width_px?.getValue?.() || 2);
    entity.polyline.material = width >= 4
      ? Cesium.Color.fromCssColorString("#f4efe3").withAlpha(0.96)
      : Cesium.Color.fromCssColorString("#eadfc9").withAlpha(0.86);
    state.groundEntities.push(entity);
  }
  if (layer === "water") {
    if (!entity.polygon) return;
    entity.polygon.material = Cesium.Color.fromCssColorString("#4d99b8").withAlpha(0.78);
    entity.polygon.outline = false;
    state.groundEntities.push(entity);
  }
  if (layer === "green") {
    if (!entity.polygon) return;
    entity.polygon.material = Cesium.Color.fromCssColorString("#7bb06f").withAlpha(0.58);
    entity.polygon.outline = false;
    state.groundEntities.push(entity);
  }
  if (layer === "no_fly_zone") {
    if (!entity.polygon) return;
    entity.polygon.material = Cesium.Color.fromCssColorString("#b83b31").withAlpha(0.34);
    entity.polygon.outline = true;
    entity.polygon.outlineColor = Cesium.Color.fromCssColorString("#ffddd8");
    state.noFlyEntities.push(entity);
  }
  if (layer === "route" || layer === "real_city_route") {
    if (!entity.polyline) return;
    entity.polyline.width = 5;
    entity.polyline.material = new Cesium.PolylineGlowMaterialProperty({
      glowPower: 0.18,
      taperPower: 0.6,
      color: Cesium.Color.fromCssColorString("#00d0a1"),
    });
    entity.polyline.clampToGround = false;
    state.routeEntities.push(entity);
  }
  if (layer === "weather_sample") {
    const turbulence = Number(entity.properties.turbulence_index.getValue());
    entity.point = new Cesium.PointGraphics({
      pixelSize: 4 + turbulence * 9,
      color: Cesium.Color.fromCssColorString(
        turbulence > 0.72 ? "#d1495b" : turbulence > 0.45 ? "#f4a261" : "#2a9d8f"
      ).withAlpha(0.84),
      outlineColor: Cesium.Color.WHITE.withAlpha(0.55),
      outlineWidth: 1,
    });
    state.weatherEntities.push(entity);
  }
}

function updateLayerVisibility() {
  const altitude = $("altitude-filter").value;
  const showBuildings = $("layer-buildings").checked;
  const renderMode = buildingRenderMode();
  const showSolidBuildings = showBuildings && renderMode !== "outline";
  const showBuildingEdges = showBuildings && renderMode !== "clean";
  const showGround = $("layer-ground").checked;
  const showNoFly = $("layer-nofly").checked;
  const showWeather = $("layer-weather").checked;
  const showRoute = $("layer-route").checked;

  state.buildingEntities.forEach((e) => {
    e.show = showSolidBuildings;
    if (e.polygon) e.polygon.outline = showBuildingEdges;
  });
  if (state.tileset) state.tileset.show = showSolidBuildings;
  if (state.groundTileset) state.groundTileset.show = showGround;
  if (state.outlineTileset) state.outlineTileset.show = showBuildingEdges;
  if (state.osmBuildings) state.osmBuildings.show = showSolidBuildings;
  state.classificationEntities.forEach((e) => {
    e.show = showBuildings;
    if (e.polygon) {
      const isLowFeature = Boolean(e.uavClassificationBuilding && correctionIsLowCityFeature(classRecordFor(e.uavClassificationBuilding)));
      e.polygon.outline = showBuildingEdges && isLowFeature;
    }
  });
  state.groundEntities.forEach((e) => { e.show = showGround; });
  state.noFlyEntities.forEach((e) => { e.show = showNoFly; });
  state.routeEntities.forEach((e) => { e.show = showRoute; });
  if (state.routePrimitives) state.routePrimitives.show = showRoute;
  state.radioProfileEntities.forEach((e) => { e.show = showRoute; });
  if (state.weatherPrimitives) state.weatherPrimitives.show = showWeather;
  state.weatherEntities.forEach((e) => {
    const entityAltitude = String(e.properties.altitude_m.getValue());
    e.show = showWeather && (altitude === "all" || altitude === entityAltitude);
  });
  restyleBuildings();
}

function fillAltitudeFilter() {
  const values = new Set();
  state.weatherFeatures.forEach((feature) => {
    const altitude = feature.properties?.altitude_m;
    if (altitude !== undefined && altitude !== null) {
      values.add(String(altitude));
    }
  });
  const select = $("altitude-filter");
  [...values].sort((a, b) => Number(a) - Number(b)).forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = `${value} m`;
    select.appendChild(option);
  });
}

function renderWeatherPrimitives() {
  if (state.weatherPrimitives) {
    viewer.scene.primitives.remove(state.weatherPrimitives);
    state.weatherPrimitives = null;
  }
  state.weatherVisibleCount = 0;
  if (!state.weatherFeatures.length) {
    updateWeatherResolutionSummary();
    return;
  }
  const points = new Cesium.PointPrimitiveCollection();
  state.weatherFeatures.forEach((feature) => {
    if (!feature.geometry || feature.geometry.type !== "Point") return;
    if (!weatherFeatureVisible(feature)) return;
    points.add(createWeatherPrimitive(feature));
    state.weatherVisibleCount += 1;
  });
  state.weatherPrimitives = viewer.scene.primitives.add(points);
  state.weatherPrimitives.show = $("layer-weather").checked;
  updateWeatherResolutionSummary();
}

async function loadWorld() {
  try {
    setStatus("正在加载世界资产");
    updateIonDependentControls();
    const dataset = DATASETS[$("dataset-select").value];
    const token = $("ion-token").value.trim();
    if (token) {
      Cesium.Ion.defaultAccessToken = token;
    }
    let terrainMode = $("terrain-mode").value;
    if (terrainMode === "world" && !token) {
      terrainMode = "ellipsoid";
      $("terrain-mode").value = "ellipsoid";
    }
    if (terrainMode === "world") {
      if (!token) {
        throw new Error("真实地形需要 Cesium Ion Token");
      }
      viewer.terrainProvider = Cesium.Terrain.fromWorldTerrain();
    } else {
      viewer.terrainProvider = new Cesium.EllipsoidTerrainProvider();
    }
    viewer.dataSources.removeAll();
    if (state.tileset) {
      viewer.scene.primitives.remove(state.tileset);
    }
    if (state.groundTileset) {
      viewer.scene.primitives.remove(state.groundTileset);
    }
    if (state.outlineTileset) {
      viewer.scene.primitives.remove(state.outlineTileset);
    }
    if (state.osmBuildings) {
      viewer.scene.primitives.remove(state.osmBuildings);
    }
    if (state.routePrimitives) {
      viewer.scene.primitives.remove(state.routePrimitives);
    }
    if (state.weatherPrimitives) {
      viewer.scene.primitives.remove(state.weatherPrimitives);
    }
    viewer.entities.removeAll();
    resetRouteDraft(true);
    clearRadioProfileOverlay();
    state.buildingEntities = [];
    state.groundEntities = [];
    state.noFlyEntities = [];
    state.weatherEntities = [];
    state.weatherFeatures = [];
    state.weatherVisibleCount = 0;
    state.routeEntities = [];
    state.sunEntities = [];
    state.radioProfileEntities = [];
    state.selectedBuilding = null;
    state.multiSelectedBuildings = [];
    state.classificationEntities = [];
    state.multiSelectionEntities = [];
    clearSelectionHighlight();
    state.tileset = null;
    state.groundTileset = null;
    state.outlineTileset = null;
    state.osmBuildings = null;
    state.routePrimitives = null;
    state.routeFocus = null;
    state.routeFeature = null;
    state.radioProfile = null;
    state.weatherPrimitives = null;
    state.buildingIndex = [];

    const summaryResp = await fetch(assetUrl(dataset.summary), { cache: "no-store" });
    if (!summaryResp.ok) {
      throw new Error(`资产不存在：${dataset.summary}`);
    }
    const summary = await summaryResp.json();
    $("world-name").textContent = summary.display_name || summary.name;
    $("stat-buildings").textContent = summary.building_count ?? "--";
    $("stat-ground").textContent = summary.ground_feature_count ?? "--";
    $("stat-nofly").textContent = summary.no_fly_zone_count ?? "--";
    $("stat-weather").textContent = summary.weather_sample_count ?? "--";
    $("stat-route").textContent = summary.route_length_m ? (summary.route_length_m / 1000).toFixed(1) : "--";
    const center = summary.center || summary.origin;
    state.center = center || null;
    state.worldCenter = center || null;
    state.worldBounds = summary.bbox || null;
    if (dataset.world) {
      await loadBuildingIndex(assetUrl(dataset.world));
    }

    let backend = $("building-backend").value;
    if (!["none", "tiles", "osm"].includes(backend)) {
      backend = "none";
      $("building-backend").value = "none";
    }
    const tileAssets = await resolveTileAssets(dataset);
    if (backend === "osm" && !token) {
      backend = tileAssets.tileset ? "tiles" : "none";
      $("building-backend").value = backend;
    }
    if (backend === "none") {
      state.worldSource = null;
    } else if (backend === "tiles" && tileAssets.tileset) {
      if (tileAssets.groundTileset) {
        const groundTilesUrl = assetUrl(tileAssets.groundTileset);
        const groundTilesResp = await fetch(groundTilesUrl, { cache: "no-store" });
        if (!groundTilesResp.ok) {
          throw new Error(`本地地面 3D Tiles 不存在：${tileAssets.groundTileset}`);
        }
        state.groundTileset = await Cesium.Cesium3DTileset.fromUrl(groundTilesUrl);
        if (Cesium.ShadowMode) {
          state.groundTileset.shadows = Cesium.ShadowMode.DISABLED;
        }
        viewer.scene.primitives.add(state.groundTileset);
      }
      const tilesUrl = assetUrl(tileAssets.tileset);
      const tilesResp = await fetch(tilesUrl, { cache: "no-store" });
      if (tilesResp.ok) {
        state.tileset = await Cesium.Cesium3DTileset.fromUrl(tilesUrl);
        if (Cesium.ShadowMode) {
          state.tileset.shadows = Cesium.ShadowMode.DISABLED;
        }
        viewer.scene.primitives.add(state.tileset);
        if (tileAssets.outlineTileset) {
          const outlineUrl = assetUrl(tileAssets.outlineTileset);
          const outlineResp = await fetch(outlineUrl, { cache: "no-store" });
          if (outlineResp.ok) {
            state.outlineTileset = await Cesium.Cesium3DTileset.fromUrl(outlineUrl);
            if (Cesium.ShadowMode) {
              state.outlineTileset.shadows = Cesium.ShadowMode.DISABLED;
            }
            viewer.scene.primitives.add(state.outlineTileset);
          }
        }
      } else {
        throw new Error(`本地 3D Tiles 不存在：${tileAssets.tileset}`);
      }
    } else if (backend === "osm") {
      const token = $("ion-token").value.trim();
      if (!token) {
        throw new Error("Cesium OSM Buildings 需要 Cesium Ion Token");
      }
      Cesium.Ion.defaultAccessToken = token;
      state.osmBuildings = await Cesium.createOsmBuildingsAsync();
      viewer.scene.primitives.add(state.osmBuildings);
    }

    if (!ROUTE_SELECTION_PAGE_CONFIG.hideDefaultRoute) {
      await loadRoutePrimitive(assetUrl(dataset.route));
    }
    if (dataset.weather) {
      await loadWeatherPrimitives(assetUrl(dataset.weather));
    }
    await loadRadioProfileForDataset($("dataset-select").value);

    $("altitude-filter").innerHTML = '<option value="all">全部高度</option>';
    fillAltitudeFilter();
    renderWeatherPrimitives();
    updateLayerVisibility();
    renderBuildingClassificationOverlays();
    applyLightingMode();
    if (center) {
      state.orbit.headingDeg = 28;
      state.orbit.pitchDeg = -26;
      state.orbit.rangeM = 1850;
      applyOrbitCamera(1.4);
    } else {
      const target = state.tileset || state.osmBuildings || state.routePrimitives;
      if (target) {
        await viewer.flyTo(target, { duration: 1.6 });
      }
    }
    setStatus("世界已加载");
  } catch (error) {
    console.error(error);
    setStatus(`加载失败：${error.message || "请检查资产和 HTTP 服务"}`);
  }
}


function routeBearingDeg(coords) {
  if (coords.length < 2) return 32.0;
  const start = coords[0];
  const end = coords[coords.length - 1];
  const lat1 = Cesium.Math.toRadians(start[1]);
  const lat2 = Cesium.Math.toRadians(end[1]);
  const dLon = Cesium.Math.toRadians(end[0] - start[0]);
  const y = Math.sin(dLon) * Math.cos(lat2);
  const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLon);
  return (Cesium.Math.toDegrees(Math.atan2(y, x)) + 360.0) % 360.0;
}

function routeFocusFromCoordinates(coords) {
  if (!coords || coords.length < 2) return null;
  const lons = coords.map((coord) => coord[0]);
  const lats = coords.map((coord) => coord[1]);
  const positions = coords.map((coord) => Cesium.Cartesian3.fromDegrees(coord[0], coord[1], coord[2] ?? 100.0));
  let lengthM = 0.0;
  for (let idx = 1; idx < positions.length; idx += 1) {
    lengthM += Cesium.Cartesian3.distance(positions[idx - 1], positions[idx]);
  }
  return {
    center: {
      lon: (Math.min(...lons) + Math.max(...lons)) / 2.0,
      lat: (Math.min(...lats) + Math.max(...lats)) / 2.0,
    },
    headingDeg: routeBearingDeg(coords),
    lengthM,
  };
}

function setOrbitView(center, headingDeg, pitchDeg, rangeM, duration = 1.0) {
  if (!center) return;
  state.center = center;
  state.orbit.headingDeg = headingDeg;
  state.orbit.pitchDeg = pitchDeg;
  state.orbit.rangeM = rangeM;
  applyOrbitCamera(duration);
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function remotePanStepMeters() {
  return Math.round(clamp(state.orbit.rangeM * 0.14, 35.0, 650.0));
}

function updateViewRemoteReadout() {
  const readout = $("view-remote-readout");
  if (!readout) return;
  if (!state.center) {
    readout.textContent = "等待世界加载。";
    return;
  }
  readout.textContent = [
    `目标 ${state.center.lon.toFixed(5)}, ${state.center.lat.toFixed(5)}`,
    `航向 ${Math.round(state.orbit.headingDeg)}°`,
    `俯仰 ${Math.round(state.orbit.pitchDeg)}°`,
    `距离 ${Math.round(state.orbit.rangeM)}m`,
    `平移步长 ${remotePanStepMeters()}m`,
  ].join("｜");
}

function panOrbitTarget(eastM, northM) {
  if (!state.center) return;
  state.center = offsetLonLat(state.center, eastM, northM);
  applyOrbitCamera(0);
}

function zoomOrbit(factor) {
  if (!state.center) return;
  state.orbit.rangeM = clamp(state.orbit.rangeM * factor, 160.0, 9000.0);
  applyOrbitCamera(0);
}

function rotateOrbit(deltaDeg) {
  if (!state.center) return;
  state.orbit.headingDeg = (state.orbit.headingDeg + deltaDeg + 360.0) % 360.0;
  applyOrbitCamera(0);
}

function pitchOrbit(deltaDeg) {
  if (!state.center) return;
  state.orbit.pitchDeg = clamp(state.orbit.pitchDeg + deltaDeg, -82.0, -10.0);
  applyOrbitCamera(0);
}

function handleViewRemoteAction(action) {
  const step = remotePanStepMeters();
  const actions = {
    "pan-north": () => panOrbitTarget(0.0, step),
    "pan-south": () => panOrbitTarget(0.0, -step),
    "pan-east": () => panOrbitTarget(step, 0.0),
    "pan-west": () => panOrbitTarget(-step, 0.0),
    "center-city": () => setOrbitView(state.worldCenter || state.center, state.orbit.headingDeg, state.orbit.pitchDeg, state.orbit.rangeM, 0),
    "zoom-in": () => zoomOrbit(0.8),
    "zoom-out": () => zoomOrbit(1.25),
    "pitch-up": () => pitchOrbit(7.0),
    "pitch-down": () => pitchOrbit(-7.0),
    "rotate-left": () => rotateOrbit(-12.0),
    "rotate-right": () => rotateOrbit(12.0),
    "route-focus": flyRoute,
    "reset-view": resetView,
  };
  actions[action]?.();
  updateViewRemoteReadout();
}

function flyRoute() {
  if (!state.routeFocus) return;
  const routeRange = Math.max(720.0, Math.min(2600.0, state.routeFocus.lengthM * 0.72));
  setOrbitView(state.routeFocus.center, (state.routeFocus.headingDeg + 28.0) % 360.0, -42.0, routeRange, 1.0);
  if (state.routeFeature) {
    setRouteSelection(state.routeFeature);
    showFeatureDetail(state.routeFeature.label, state.routeFeature.properties);
  }
}

function flyOblique() {
  setOrbitView(state.worldCenter || state.center, 38.0, -34.0, 1700.0, 1.0);
}

function flyTopdown() {
  setOrbitView(state.worldCenter || state.center, 0.0, -82.0, 2450.0, 1.0);
}

function resetView() {
  if (state.worldCenter || state.center) {
    setOrbitView(state.worldCenter || state.center, 12.0, -54.0, 3300.0, 1.0);
  } else if (state.worldSource) {
    viewer.flyTo(state.tileset || state.routePrimitives, { duration: 1.2 });
  }
}

function applyOrbitCamera(duration = 0) {
  if (!state.center) return;
  const target = Cesium.Cartesian3.fromDegrees(state.center.lon, state.center.lat, 0.0);
  const offset = new Cesium.HeadingPitchRange(
    Cesium.Math.toRadians(state.orbit.headingDeg),
    Cesium.Math.toRadians(state.orbit.pitchDeg),
    state.orbit.rangeM
  );
  if (duration > 0) {
    viewer.camera.flyToBoundingSphere(
      new Cesium.BoundingSphere(target, Math.max(120.0, state.orbit.rangeM * 0.12)),
      { offset, duration }
    );
  } else {
    viewer.camera.lookAt(target, offset);
    viewer.camera.lookAtTransform(Cesium.Matrix4.IDENTITY);
    window.__orbitDebug.applied += 1;
  }
  updateViewRemoteReadout();
}

viewer.selectedEntityChanged.addEventListener((entity) => {
  if (!entity || !entity.properties) {
    $("feature-detail").textContent = "点击地图对象查看属性。";
    return;
  }
  const props = {};
  entity.properties.propertyNames.forEach((name) => {
    props[name] = entity.properties[name].getValue();
  });
  showFeatureDetail("实体属性", props);
});

async function loadRoutePrimitive(url) {
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`航线资产不存在：${url}`);
  }
  const geo = await resp.json();
  const feature = geo.features && geo.features[0];
  if (!feature || !feature.geometry || feature.geometry.type !== "LineString") {
    throw new Error("航线数据格式错误");
  }
  const positions = feature.geometry.coordinates.map((c) => Cesium.Cartesian3.fromDegrees(c[0], c[1], c[2] || 100.0));
  const collection = new Cesium.PolylineCollection();
  state.routeFeature = {
    type: "route",
    label: "航线属性",
    properties: feature.properties || {},
    coordinates: feature.geometry.coordinates,
  };
  state.routeFocus = routeFocusFromCoordinates(feature.geometry.coordinates);
  collection.add({
    positions,
    width: 4,
    id: {
      uavFeature: state.routeFeature,
    },
    material: Cesium.Material.fromType("Color", {
      color: Cesium.Color.fromCssColorString("#00d0a1").withAlpha(0.92),
    }),
  });
  state.routePrimitives = viewer.scene.primitives.add(collection);
}

async function loadWeatherPrimitives(url) {
  const resp = await fetch(url);
  if (!resp.ok) return;
  const geo = await resp.json();
  state.weatherFeatures = (geo.features || [])
    .filter((feature) => feature.geometry?.type === "Point")
    .slice(0, 300);
}

$("btn-load").addEventListener("click", loadWorld);
$("btn-fly-route").addEventListener("click", flyRoute);
$("btn-oblique").addEventListener("click", flyOblique);
$("btn-topdown").addEventListener("click", flyTopdown);
$("btn-reset").addEventListener("click", resetView);
$("btn-route-draw-start").addEventListener("click", startRouteDrawing);
$("btn-route-draw-finish").addEventListener("click", finishRouteDrawing);
$("btn-route-draw-undo").addEventListener("click", undoRouteDraftWaypoint);
$("btn-route-draw-clear").addEventListener("click", clearRouteDraft);
$("btn-route-draw-save").addEventListener("click", () => {
  saveRouteDraft().catch((error) => {
    console.error(error);
    setRouteDrawStatus(`保存失败：${error.message || error}`);
  });
});
["route-draw-altitude", "route-draw-speed", "route-draw-altitude-mode", "route-draw-name"].forEach((id) => {
  $(id).addEventListener("input", syncRouteDraftUI);
  $(id).addEventListener("change", syncRouteDraftUI);
});
$("dataset-select").addEventListener("change", async () => {
  resetDeleteConfirmation();
  resetRouteDraft(true);
  clearMultiSelection(false);
  clearSelectionHighlight();
  applySavedRadioProfileSettings($("dataset-select").value);
  updateRadioDensityNote();
  state.selectedBuilding = null;
  refreshCorrectionVersionSelect();
  applyDefaultCorrectionColorMode();
  await loadBuildingClassifications();
  renderBuildingClassificationOverlays();
  updateBuildingClassEditor();
});
$("radio-sample-filter").addEventListener("change", () => {
  rerenderRadioPointCloud();
  saveRadioProfileSettings();
});
$("radio-density-select").addEventListener("change", () => {
  reloadRadioPointCloudForControls().catch((error) => {
    console.warn("无线电点云密度切换失败", error);
    updateRadioDensityNote();
  });
  saveRadioProfileSettings();
});
$("btn-toggle-left").addEventListener("click", () => togglePanel("left"));
$("btn-toggle-right").addEventListener("click", () => togglePanel("right"));
$("btn-apply-class").addEventListener("click", applySelectedBuildingClass);
$("btn-clear-class").addEventListener("click", clearSelectedBuildingClass);
$("btn-save-new-class-version").addEventListener("click", () => saveCorrectionVersion("new"));
$("btn-overwrite-class-version").addEventListener("click", () => saveCorrectionVersion("overwrite"));
$("btn-set-default-class-version").addEventListener("click", setDefaultCorrectionVersion);
$("btn-delete-class-version").addEventListener("click", deleteCurrentCorrectionVersion);
$("building-class-select").addEventListener("change", markClassEditorTouched);
$("building-class-note").addEventListener("input", markClassEditorTouched);
$("building-class-version").addEventListener("change", async () => {
  resetDeleteConfirmation();
  await loadBuildingClassifications();
  updateCorrectionSaveControls();
  await loadWorld();
});
$("building-class-color-mode").addEventListener("change", () => {
  state.correctionColorMode = correctionColorMode();
  renderBuildingClassificationOverlays();
});
[...document.querySelectorAll("[data-view-action]")].forEach((button) => {
  button.addEventListener("click", () => handleViewRemoteAction(button.dataset.viewAction));
});
["layer-buildings", "layer-ground", "layer-nofly", "layer-weather", "layer-route", "render-mode", "building-backend", "terrain-mode"].forEach((id) => {
  $(id).addEventListener("change", updateLayerVisibility);
});
["altitude-filter", "weather-grid-mode", "weather-altitude-mode"].forEach((id) => {
  $(id).addEventListener("change", () => {
    clearSelectionHighlight();
    renderWeatherPrimitives();
    updateLayerVisibility();
  });
});
$("building-backend").addEventListener("change", loadWorld);
$("terrain-mode").addEventListener("change", loadWorld);
$("lighting-mode").addEventListener("change", applyLightingMode);
$("sun-cycle").addEventListener("change", applyLightingMode);
$("ion-token").addEventListener("input", updateIonDependentControls);

updatePanelToggleButtons();
updateIonDependentControls();
updateViewRemoteReadout();
updateBuildingClassEditor();
syncRouteDraftUI();
(async () => {
  await loadCorrectionVersionIndex();
  applyDefaultCorrectionColorMode();
  await loadBuildingClassifications();
  await loadRadioProfileSettings();
  updateBuildingClassEditor();
  await loadWorld();
})();
