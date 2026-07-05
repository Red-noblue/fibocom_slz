/* COPYRIGHT HEADER GOES HERE: No CopyRight Header String Passed During Model Conversion */

/* Command Line used:
qnn-onnx-converter; act_bitwidth=8; act_quantizer=tf; act_quantizer_calibration=min-max; act_quantizer_schema=asymmetric; adjust_nms_features_dims=True; algorithms=[]; align_matmul_ranks=True; apply_masked_softmax=uncompressed; arch_checker=False; batch=None; bias_bitwidth=8; converter_op_package_lib=; copyright_file=None; custom_io=; custom_op_config_paths=None; debug=-1; defer_loading=False; define_symbol=None; disable_batchnorm_folding=False; disable_node_validation=False; disable_qnn_op_config_validation=False; disable_relu_squashing=False; dry_run=None; dumpIR=False; dump_custom_io_config_template=; dump_encoding_json=False; dump_inferred_model=False; dump_qairt_io_config_yaml=; dump_qairt_quantizer_command=None; dump_value_info=False; enable_framework_trace=False; enable_match_gathernd=False; enable_per_row_quantized_bias=False; exclude_named_tensors=False; expand_gru_op_structure=True; expand_lstm_op_structure=False; expand_sparse_op_structure=False; export_format=cpp; extract_color_transform=True; float_bias_bitwidth=0; float_bias_bw=0; float_bitwidth=32; float_bw=32; float_fallback=False; force_prune_cast_ops=False; handle_gather_negative_indices=True; ignore_encodings=False; include_data_invariant_ops=False; inject_cast_for_gather=True; input_dim=None; input_dtype=[]; input_encoding=[]; input_layout=[]; input_list=/workspace/modules/fiboaistack_229_env/calibration/input_list.txt; input_type=[]; keep_disconnected_nodes=False; keep_int64_inputs=False; keep_quant_nodes=False; keep_weights_quantized=False; match_caffe_ssd_to_tf=True; model_version=None; multi_time_steps_gru=False; multi_time_steps_lstm=False; no_simplification=False; op_package_lib=; out_names=['output', 'output']; overwrite_model_prefix=False; pack_4_bit_weights=False; package_name=None; packed_masked_softmax_inputs=[]; packed_max_seq=1; param_quantizer=None; param_quantizer_calibration=min-max; param_quantizer_schema=asymmetric; percentile_calibration_value=99.99; perform_axes_to_spatial_first_order=True; perform_layout_transformation=False; prepare_inputs_as_params=False; preprocess_roi_pool_inputs=True; preserve_io=[]; quantization_overrides=; restrict_quantization_steps=[]; squash_box_decoder=True; unroll_gru_time_steps=True; unroll_lstm_time_steps=True; use_aimet_quantizer=False; use_convert_quantization_nodes=False; use_dynamic_16_bit_weights=False; use_native_dtype=False; use_native_input_files=False; use_native_output_files=False; use_per_channel_quantization=False; use_per_row_quantization=False; validate_models=False; weights_bitwidth=8
*/

#include "QnnOpDef.h"
#include "QnnModel.hpp"

// Flag to determine if Backend should do node validation for each opNode added
#define DO_GRAPH_NODE_VALIDATIONS 1

using namespace qnn_wrapper_api;
const __attribute__((visibility("default"))) char* QNN_SDK_VERSION = "qaisw-v2.29.0.241129103708_105762";
extern "C" {
static ModelError_t addTensor_input(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_input[] = {1, 256, 256, 7};
  VALIDATE(model.addTensor("input", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "input",
                                 .type= QNN_TENSOR_TYPE_APP_WRITE,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0392201766371727f, .offset= -130}}},
                                 .rank= 4,
                                 .dimensions=dimensions_input,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=nullptr,
                                                .dataSize=0}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor_enc1_c1_depth_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_enc1_c1_depth_weight[] = {3, 3, 1, 7};
  VALIDATE(model.addTensor("enc1_c1_depth_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "enc1_c1_depth_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0025894374120981f, .offset= -134}}},
                                 .rank= 4,
                                 .dimensions=dimensions_enc1_c1_depth_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(enc1_c1_depth_weight),
                                                .dataSize=BINLEN(enc1_c1_depth_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__enc1_c1_depth_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__enc1_c1_depth_Conv_bias[] = {7};
  VALIDATE(model.addTensor("_enc1_c1_depth_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_enc1_c1_depth_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__enc1_c1_depth_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_enc1_c1_depth_Conv_bias),
                                                .dataSize=BINLEN(_enc1_c1_depth_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__enc1_c1_depth_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _enc1_c1_depth_Conv */
  uint32_t dimensions___enc1_c1_depth_Conv_dilation[] = {2};
  uint32_t __enc1_c1_depth_Conv_dilation[] = {1, 1};
  uint32_t dimensions___enc1_c1_depth_Conv_pad_amount[] = {2, 2};
  uint32_t __enc1_c1_depth_Conv_pad_amount[] = {1, 1, 1, 1};
  uint32_t dimensions___enc1_c1_depth_Conv_stride[] = {2};
  uint32_t __enc1_c1_depth_Conv_stride[] = {1, 1};
  Qnn_Param_t params__enc1_c1_depth_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc1_c1_depth_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___enc1_c1_depth_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc1_c1_depth_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc1_c1_depth_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___enc1_c1_depth_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc1_c1_depth_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc1_c1_depth_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___enc1_c1_depth_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc1_c1_depth_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}}
  };
  const char*  inputs__enc1_c1_depth_Conv[] = {
    "input",
    "enc1_c1_depth_weight",
    "_enc1_c1_depth_Conv_bias"
  };
  uint32_t dimensions__enc1_c1_depth_Conv_output_0[] = {1, 256, 256, 7};
  Qnn_Tensor_t outputs__enc1_c1_depth_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_enc1_c1_depth_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0249061621725559f, .offset= -121}}},
            .rank= 4,
            .dimensions=dimensions__enc1_c1_depth_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_enc1_c1_depth_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "DepthWiseConv2d", // Qnn Node Type
                         params__enc1_c1_depth_Conv, // Node Params
                         3, // Num Node Params
                         inputs__enc1_c1_depth_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__enc1_c1_depth_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_enc1_c1_point_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_enc1_c1_point_weight[] = {1, 1, 7, 48};
  VALIDATE(model.addTensor("enc1_c1_point_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "enc1_c1_point_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0033073746599257f, .offset= -129}}},
                                 .rank= 4,
                                 .dimensions=dimensions_enc1_c1_point_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(enc1_c1_point_weight),
                                                .dataSize=BINLEN(enc1_c1_point_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__enc1_c1_point_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__enc1_c1_point_Conv_bias[] = {48};
  VALIDATE(model.addTensor("_enc1_c1_point_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_enc1_c1_point_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__enc1_c1_point_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_enc1_c1_point_Conv_bias),
                                                .dataSize=BINLEN(_enc1_c1_point_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__enc1_c1_point_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _enc1_c1_point_Conv */
  uint32_t dimensions___enc1_c1_point_Conv_dilation[] = {2};
  uint32_t __enc1_c1_point_Conv_dilation[] = {1, 1};
  uint32_t dimensions___enc1_c1_point_Conv_pad_amount[] = {2, 2};
  uint32_t __enc1_c1_point_Conv_pad_amount[] = {0, 0, 0, 0};
  uint32_t dimensions___enc1_c1_point_Conv_stride[] = {2};
  uint32_t __enc1_c1_point_Conv_stride[] = {1, 1};
  Qnn_Param_t params__enc1_c1_point_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc1_c1_point_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___enc1_c1_point_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc1_c1_point_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc1_c1_point_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___enc1_c1_point_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc1_c1_point_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc1_c1_point_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___enc1_c1_point_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc1_c1_point_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 1}}}}
  };
  const char*  inputs__enc1_c1_point_Conv[] = {
    "_enc1_c1_depth_Conv_output_0",
    "enc1_c1_point_weight",
    "_enc1_c1_point_Conv_bias"
  };
  uint32_t dimensions__enc1_c1_point_Conv_output_0[] = {1, 256, 256, 48};
  Qnn_Tensor_t outputs__enc1_c1_point_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_enc1_c1_point_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0165122784674168f, .offset= -132}}},
            .rank= 4,
            .dimensions=dimensions__enc1_c1_point_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_enc1_c1_point_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "Conv2d", // Qnn Node Type
                         params__enc1_c1_point_Conv, // Node Params
                         4, // Num Node Params
                         inputs__enc1_c1_point_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__enc1_c1_point_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Mul_728(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Mul_728[] = {48};
  VALIDATE(model.addTensor("onnx__Mul_728", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Mul_728",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0047282385639846f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Mul_728,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Mul_728),
                                                .dataSize=BINLEN(onnx__Mul_728)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Add_729(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Add_729[] = {48};
  VALIDATE(model.addTensor("onnx__Add_729", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Add_729",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0009506414644420f, .offset= -63}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Add_729,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Add_729),
                                                .dataSize=BINLEN(onnx__Add_729)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__enc1_c1_norm_Reshape_GroupNorm(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _enc1_c1_norm_Reshape_GroupNorm */
  Qnn_Param_t params__enc1_c1_norm_Reshape_GroupNorm[] = {
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="epsilon",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_FLOAT_32, {.floatValue = 0.000010000000f}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 8}}}}
  };
  const char*  inputs__enc1_c1_norm_Reshape_GroupNorm[] = {
    "_enc1_c1_point_Conv_output_0",
    "onnx__Mul_728",
    "onnx__Add_729"
  };
  uint32_t dimensions__enc1_c1_act_Relu_output_0[] = {1, 256, 256, 48};
  Qnn_Tensor_t outputs__enc1_c1_norm_Reshape_GroupNorm[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_enc1_c1_act_Relu_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0261491686105728f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__enc1_c1_act_Relu_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_enc1_c1_norm_Reshape_GroupNorm", // Node Name
                         "qti.aisw", // Package Name
                         "GroupNorm", // Qnn Node Type
                         params__enc1_c1_norm_Reshape_GroupNorm, // Node Params
                         2, // Num Node Params
                         inputs__enc1_c1_norm_Reshape_GroupNorm, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__enc1_c1_norm_Reshape_GroupNorm, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_enc1_c2_depth_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_enc1_c2_depth_weight[] = {3, 3, 1, 48};
  VALIDATE(model.addTensor("enc1_c2_depth_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "enc1_c2_depth_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0032372495625168f, .offset= -112}}},
                                 .rank= 4,
                                 .dimensions=dimensions_enc1_c2_depth_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(enc1_c2_depth_weight),
                                                .dataSize=BINLEN(enc1_c2_depth_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__enc1_c2_depth_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__enc1_c2_depth_Conv_bias[] = {48};
  VALIDATE(model.addTensor("_enc1_c2_depth_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_enc1_c2_depth_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__enc1_c2_depth_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_enc1_c2_depth_Conv_bias),
                                                .dataSize=BINLEN(_enc1_c2_depth_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__enc1_c2_depth_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _enc1_c2_depth_Conv */
  uint32_t dimensions___enc1_c2_depth_Conv_dilation[] = {2};
  uint32_t __enc1_c2_depth_Conv_dilation[] = {1, 1};
  uint32_t dimensions___enc1_c2_depth_Conv_pad_amount[] = {2, 2};
  uint32_t __enc1_c2_depth_Conv_pad_amount[] = {1, 1, 1, 1};
  uint32_t dimensions___enc1_c2_depth_Conv_stride[] = {2};
  uint32_t __enc1_c2_depth_Conv_stride[] = {1, 1};
  Qnn_Param_t params__enc1_c2_depth_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc1_c2_depth_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___enc1_c2_depth_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc1_c2_depth_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc1_c2_depth_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___enc1_c2_depth_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc1_c2_depth_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc1_c2_depth_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___enc1_c2_depth_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc1_c2_depth_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}}
  };
  const char*  inputs__enc1_c2_depth_Conv[] = {
    "_enc1_c1_act_Relu_output_0",
    "enc1_c2_depth_weight",
    "_enc1_c2_depth_Conv_bias"
  };
  uint32_t dimensions__enc1_c2_depth_Conv_output_0[] = {1, 256, 256, 48};
  Qnn_Tensor_t outputs__enc1_c2_depth_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_enc1_c2_depth_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0269231554120779f, .offset= -116}}},
            .rank= 4,
            .dimensions=dimensions__enc1_c2_depth_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_enc1_c2_depth_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "DepthWiseConv2d", // Qnn Node Type
                         params__enc1_c2_depth_Conv, // Node Params
                         3, // Num Node Params
                         inputs__enc1_c2_depth_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__enc1_c2_depth_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_enc1_c2_point_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_enc1_c2_point_weight[] = {1, 1, 48, 48};
  VALIDATE(model.addTensor("enc1_c2_point_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "enc1_c2_point_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0043795811943710f, .offset= -125}}},
                                 .rank= 4,
                                 .dimensions=dimensions_enc1_c2_point_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(enc1_c2_point_weight),
                                                .dataSize=BINLEN(enc1_c2_point_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__enc1_c2_point_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__enc1_c2_point_Conv_bias[] = {48};
  VALIDATE(model.addTensor("_enc1_c2_point_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_enc1_c2_point_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__enc1_c2_point_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_enc1_c2_point_Conv_bias),
                                                .dataSize=BINLEN(_enc1_c2_point_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__enc1_c2_point_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _enc1_c2_point_Conv */
  uint32_t dimensions___enc1_c2_point_Conv_dilation[] = {2};
  uint32_t __enc1_c2_point_Conv_dilation[] = {1, 1};
  uint32_t dimensions___enc1_c2_point_Conv_pad_amount[] = {2, 2};
  uint32_t __enc1_c2_point_Conv_pad_amount[] = {0, 0, 0, 0};
  uint32_t dimensions___enc1_c2_point_Conv_stride[] = {2};
  uint32_t __enc1_c2_point_Conv_stride[] = {1, 1};
  Qnn_Param_t params__enc1_c2_point_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc1_c2_point_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___enc1_c2_point_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc1_c2_point_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc1_c2_point_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___enc1_c2_point_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc1_c2_point_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc1_c2_point_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___enc1_c2_point_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc1_c2_point_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 1}}}}
  };
  const char*  inputs__enc1_c2_point_Conv[] = {
    "_enc1_c2_depth_Conv_output_0",
    "enc1_c2_point_weight",
    "_enc1_c2_point_Conv_bias"
  };
  uint32_t dimensions__enc1_c2_point_Conv_output_0[] = {1, 256, 256, 48};
  Qnn_Tensor_t outputs__enc1_c2_point_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_enc1_c2_point_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0164620261639357f, .offset= -129}}},
            .rank= 4,
            .dimensions=dimensions__enc1_c2_point_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_enc1_c2_point_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "Conv2d", // Qnn Node Type
                         params__enc1_c2_point_Conv, // Node Params
                         4, // Num Node Params
                         inputs__enc1_c2_point_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__enc1_c2_point_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Mul_735(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Mul_735[] = {48};
  VALIDATE(model.addTensor("onnx__Mul_735", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Mul_735",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0049559022299945f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Mul_735,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Mul_735),
                                                .dataSize=BINLEN(onnx__Mul_735)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Add_736(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Add_736[] = {48};
  VALIDATE(model.addTensor("onnx__Add_736", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Add_736",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0005062331329100f, .offset= -91}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Add_736,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Add_736),
                                                .dataSize=BINLEN(onnx__Add_736)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__enc1_c2_norm_Reshape_GroupNorm(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _enc1_c2_norm_Reshape_GroupNorm */
  Qnn_Param_t params__enc1_c2_norm_Reshape_GroupNorm[] = {
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="epsilon",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_FLOAT_32, {.floatValue = 0.000010000000f}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 8}}}}
  };
  const char*  inputs__enc1_c2_norm_Reshape_GroupNorm[] = {
    "_enc1_c2_point_Conv_output_0",
    "onnx__Mul_735",
    "onnx__Add_736"
  };
  uint32_t dimensions__enc1_c2_act_Relu_output_0[] = {1, 256, 256, 48};
  Qnn_Tensor_t outputs__enc1_c2_norm_Reshape_GroupNorm[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_enc1_c2_act_Relu_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0351408384740353f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__enc1_c2_act_Relu_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_enc1_c2_norm_Reshape_GroupNorm", // Node Name
                         "qti.aisw", // Package Name
                         "GroupNorm", // Qnn Node Type
                         params__enc1_c2_norm_Reshape_GroupNorm, // Node Params
                         2, // Num Node Params
                         inputs__enc1_c2_norm_Reshape_GroupNorm, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__enc1_c2_norm_Reshape_GroupNorm, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addNode__pool_AveragePool(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _pool_AveragePool */
  uint32_t dimensions___pool_AveragePool_filter_size[] = {2};
  uint32_t __pool_AveragePool_filter_size[] = {2, 2};
  uint32_t dimensions___pool_AveragePool_pad_amount[] = {2, 2};
  uint32_t __pool_AveragePool_pad_amount[] = {0, 0, 0, 0};
  uint32_t dimensions___pool_AveragePool_stride[] = {2};
  uint32_t __pool_AveragePool_stride[] = {2, 2};
  Qnn_Param_t params__pool_AveragePool[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="filter_size",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__pool_AveragePool_filter_size",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___pool_AveragePool_filter_size,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__pool_AveragePool_filter_size,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__pool_AveragePool_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___pool_AveragePool_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__pool_AveragePool_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__pool_AveragePool_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___pool_AveragePool_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__pool_AveragePool_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="count_pad_for_edges",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_BOOL_8, {.bool8Value = 1}}}}
  };
  const char*  inputs__pool_AveragePool[] = {
    "_enc1_c2_act_Relu_output_0"
  };
  uint32_t dimensions__pool_AveragePool_output_0[] = {1, 128, 128, 48};
  Qnn_Tensor_t outputs__pool_AveragePool[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_pool_AveragePool_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0135178938508034f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__pool_AveragePool_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_pool_AveragePool", // Node Name
                         "qti.aisw", // Package Name
                         "PoolAvg2d", // Qnn Node Type
                         params__pool_AveragePool, // Node Params
                         4, // Num Node Params
                         inputs__pool_AveragePool, // Input Tensor Names
                         1, // Num Input Tensor Names
                         outputs__pool_AveragePool, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_enc2_c1_depth_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_enc2_c1_depth_weight[] = {3, 3, 1, 48};
  VALIDATE(model.addTensor("enc2_c1_depth_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "enc2_c1_depth_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0027796630747616f, .offset= -126}}},
                                 .rank= 4,
                                 .dimensions=dimensions_enc2_c1_depth_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(enc2_c1_depth_weight),
                                                .dataSize=BINLEN(enc2_c1_depth_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__enc2_c1_depth_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__enc2_c1_depth_Conv_bias[] = {48};
  VALIDATE(model.addTensor("_enc2_c1_depth_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_enc2_c1_depth_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__enc2_c1_depth_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_enc2_c1_depth_Conv_bias),
                                                .dataSize=BINLEN(_enc2_c1_depth_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__enc2_c1_depth_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _enc2_c1_depth_Conv */
  uint32_t dimensions___enc2_c1_depth_Conv_dilation[] = {2};
  uint32_t __enc2_c1_depth_Conv_dilation[] = {1, 1};
  uint32_t dimensions___enc2_c1_depth_Conv_pad_amount[] = {2, 2};
  uint32_t __enc2_c1_depth_Conv_pad_amount[] = {1, 1, 1, 1};
  uint32_t dimensions___enc2_c1_depth_Conv_stride[] = {2};
  uint32_t __enc2_c1_depth_Conv_stride[] = {1, 1};
  Qnn_Param_t params__enc2_c1_depth_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc2_c1_depth_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___enc2_c1_depth_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc2_c1_depth_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc2_c1_depth_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___enc2_c1_depth_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc2_c1_depth_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc2_c1_depth_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___enc2_c1_depth_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc2_c1_depth_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}}
  };
  const char*  inputs__enc2_c1_depth_Conv[] = {
    "_pool_AveragePool_output_0",
    "enc2_c1_depth_weight",
    "_enc2_c1_depth_Conv_bias"
  };
  uint32_t dimensions__enc2_c1_depth_Conv_output_0[] = {1, 128, 128, 48};
  Qnn_Tensor_t outputs__enc2_c1_depth_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_enc2_c1_depth_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0148890595883131f, .offset= -104}}},
            .rank= 4,
            .dimensions=dimensions__enc2_c1_depth_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_enc2_c1_depth_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "DepthWiseConv2d", // Qnn Node Type
                         params__enc2_c1_depth_Conv, // Node Params
                         3, // Num Node Params
                         inputs__enc2_c1_depth_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__enc2_c1_depth_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_enc2_c1_point_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_enc2_c1_point_weight[] = {1, 1, 48, 96};
  VALIDATE(model.addTensor("enc2_c1_point_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "enc2_c1_point_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0022748422343284f, .offset= -128}}},
                                 .rank= 4,
                                 .dimensions=dimensions_enc2_c1_point_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(enc2_c1_point_weight),
                                                .dataSize=BINLEN(enc2_c1_point_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__enc2_c1_point_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__enc2_c1_point_Conv_bias[] = {96};
  VALIDATE(model.addTensor("_enc2_c1_point_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_enc2_c1_point_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__enc2_c1_point_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_enc2_c1_point_Conv_bias),
                                                .dataSize=BINLEN(_enc2_c1_point_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__enc2_c1_point_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _enc2_c1_point_Conv */
  uint32_t dimensions___enc2_c1_point_Conv_dilation[] = {2};
  uint32_t __enc2_c1_point_Conv_dilation[] = {1, 1};
  uint32_t dimensions___enc2_c1_point_Conv_pad_amount[] = {2, 2};
  uint32_t __enc2_c1_point_Conv_pad_amount[] = {0, 0, 0, 0};
  uint32_t dimensions___enc2_c1_point_Conv_stride[] = {2};
  uint32_t __enc2_c1_point_Conv_stride[] = {1, 1};
  Qnn_Param_t params__enc2_c1_point_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc2_c1_point_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___enc2_c1_point_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc2_c1_point_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc2_c1_point_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___enc2_c1_point_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc2_c1_point_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc2_c1_point_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___enc2_c1_point_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc2_c1_point_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 1}}}}
  };
  const char*  inputs__enc2_c1_point_Conv[] = {
    "_enc2_c1_depth_Conv_output_0",
    "enc2_c1_point_weight",
    "_enc2_c1_point_Conv_bias"
  };
  uint32_t dimensions__enc2_c1_point_Conv_output_0[] = {1, 128, 128, 96};
  Qnn_Tensor_t outputs__enc2_c1_point_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_enc2_c1_point_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0071325618773699f, .offset= -117}}},
            .rank= 4,
            .dimensions=dimensions__enc2_c1_point_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_enc2_c1_point_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "Conv2d", // Qnn Node Type
                         params__enc2_c1_point_Conv, // Node Params
                         4, // Num Node Params
                         inputs__enc2_c1_point_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__enc2_c1_point_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Mul_742(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Mul_742[] = {96};
  VALIDATE(model.addTensor("onnx__Mul_742", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Mul_742",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0042749689891934f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Mul_742,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Mul_742),
                                                .dataSize=BINLEN(onnx__Mul_742)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Add_743(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Add_743[] = {96};
  VALIDATE(model.addTensor("onnx__Add_743", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Add_743",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0003247986023780f, .offset= -119}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Add_743,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Add_743),
                                                .dataSize=BINLEN(onnx__Add_743)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__enc2_c1_norm_Reshape_GroupNorm(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _enc2_c1_norm_Reshape_GroupNorm */
  Qnn_Param_t params__enc2_c1_norm_Reshape_GroupNorm[] = {
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="epsilon",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_FLOAT_32, {.floatValue = 0.000010000000f}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 8}}}}
  };
  const char*  inputs__enc2_c1_norm_Reshape_GroupNorm[] = {
    "_enc2_c1_point_Conv_output_0",
    "onnx__Mul_742",
    "onnx__Add_743"
  };
  uint32_t dimensions__enc2_c1_act_Relu_output_0[] = {1, 128, 128, 96};
  Qnn_Tensor_t outputs__enc2_c1_norm_Reshape_GroupNorm[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_enc2_c1_act_Relu_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0200686790049076f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__enc2_c1_act_Relu_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_enc2_c1_norm_Reshape_GroupNorm", // Node Name
                         "qti.aisw", // Package Name
                         "GroupNorm", // Qnn Node Type
                         params__enc2_c1_norm_Reshape_GroupNorm, // Node Params
                         2, // Num Node Params
                         inputs__enc2_c1_norm_Reshape_GroupNorm, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__enc2_c1_norm_Reshape_GroupNorm, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_enc2_c2_depth_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_enc2_c2_depth_weight[] = {3, 3, 1, 96};
  VALIDATE(model.addTensor("enc2_c2_depth_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "enc2_c2_depth_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0031584566459060f, .offset= -123}}},
                                 .rank= 4,
                                 .dimensions=dimensions_enc2_c2_depth_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(enc2_c2_depth_weight),
                                                .dataSize=BINLEN(enc2_c2_depth_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__enc2_c2_depth_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__enc2_c2_depth_Conv_bias[] = {96};
  VALIDATE(model.addTensor("_enc2_c2_depth_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_enc2_c2_depth_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__enc2_c2_depth_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_enc2_c2_depth_Conv_bias),
                                                .dataSize=BINLEN(_enc2_c2_depth_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__enc2_c2_depth_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _enc2_c2_depth_Conv */
  uint32_t dimensions___enc2_c2_depth_Conv_dilation[] = {2};
  uint32_t __enc2_c2_depth_Conv_dilation[] = {1, 1};
  uint32_t dimensions___enc2_c2_depth_Conv_pad_amount[] = {2, 2};
  uint32_t __enc2_c2_depth_Conv_pad_amount[] = {1, 1, 1, 1};
  uint32_t dimensions___enc2_c2_depth_Conv_stride[] = {2};
  uint32_t __enc2_c2_depth_Conv_stride[] = {1, 1};
  Qnn_Param_t params__enc2_c2_depth_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc2_c2_depth_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___enc2_c2_depth_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc2_c2_depth_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc2_c2_depth_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___enc2_c2_depth_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc2_c2_depth_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc2_c2_depth_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___enc2_c2_depth_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc2_c2_depth_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}}
  };
  const char*  inputs__enc2_c2_depth_Conv[] = {
    "_enc2_c1_act_Relu_output_0",
    "enc2_c2_depth_weight",
    "_enc2_c2_depth_Conv_bias"
  };
  uint32_t dimensions__enc2_c2_depth_Conv_output_0[] = {1, 128, 128, 96};
  Qnn_Tensor_t outputs__enc2_c2_depth_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_enc2_c2_depth_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0197088588029146f, .offset= -111}}},
            .rank= 4,
            .dimensions=dimensions__enc2_c2_depth_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_enc2_c2_depth_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "DepthWiseConv2d", // Qnn Node Type
                         params__enc2_c2_depth_Conv, // Node Params
                         3, // Num Node Params
                         inputs__enc2_c2_depth_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__enc2_c2_depth_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_enc2_c2_point_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_enc2_c2_point_weight[] = {1, 1, 96, 96};
  VALIDATE(model.addTensor("enc2_c2_point_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "enc2_c2_point_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0019506256794557f, .offset= -109}}},
                                 .rank= 4,
                                 .dimensions=dimensions_enc2_c2_point_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(enc2_c2_point_weight),
                                                .dataSize=BINLEN(enc2_c2_point_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__enc2_c2_point_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__enc2_c2_point_Conv_bias[] = {96};
  VALIDATE(model.addTensor("_enc2_c2_point_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_enc2_c2_point_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__enc2_c2_point_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_enc2_c2_point_Conv_bias),
                                                .dataSize=BINLEN(_enc2_c2_point_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__enc2_c2_point_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _enc2_c2_point_Conv */
  uint32_t dimensions___enc2_c2_point_Conv_dilation[] = {2};
  uint32_t __enc2_c2_point_Conv_dilation[] = {1, 1};
  uint32_t dimensions___enc2_c2_point_Conv_pad_amount[] = {2, 2};
  uint32_t __enc2_c2_point_Conv_pad_amount[] = {0, 0, 0, 0};
  uint32_t dimensions___enc2_c2_point_Conv_stride[] = {2};
  uint32_t __enc2_c2_point_Conv_stride[] = {1, 1};
  Qnn_Param_t params__enc2_c2_point_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc2_c2_point_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___enc2_c2_point_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc2_c2_point_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc2_c2_point_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___enc2_c2_point_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc2_c2_point_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc2_c2_point_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___enc2_c2_point_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc2_c2_point_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 1}}}}
  };
  const char*  inputs__enc2_c2_point_Conv[] = {
    "_enc2_c2_depth_Conv_output_0",
    "enc2_c2_point_weight",
    "_enc2_c2_point_Conv_bias"
  };
  uint32_t dimensions__enc2_c2_point_Conv_output_0[] = {1, 128, 128, 96};
  Qnn_Tensor_t outputs__enc2_c2_point_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_enc2_c2_point_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0111869452521205f, .offset= -127}}},
            .rank= 4,
            .dimensions=dimensions__enc2_c2_point_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_enc2_c2_point_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "Conv2d", // Qnn Node Type
                         params__enc2_c2_point_Conv, // Node Params
                         4, // Num Node Params
                         inputs__enc2_c2_point_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__enc2_c2_point_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Mul_749(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Mul_749[] = {96};
  VALIDATE(model.addTensor("onnx__Mul_749", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Mul_749",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0043515730649233f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Mul_749,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Mul_749),
                                                .dataSize=BINLEN(onnx__Mul_749)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Add_750(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Add_750[] = {96};
  VALIDATE(model.addTensor("onnx__Add_750", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Add_750",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0004917489713989f, .offset= -160}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Add_750,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Add_750),
                                                .dataSize=BINLEN(onnx__Add_750)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__enc2_c2_norm_Reshape_GroupNorm(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _enc2_c2_norm_Reshape_GroupNorm */
  Qnn_Param_t params__enc2_c2_norm_Reshape_GroupNorm[] = {
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="epsilon",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_FLOAT_32, {.floatValue = 0.000010000000f}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 8}}}}
  };
  const char*  inputs__enc2_c2_norm_Reshape_GroupNorm[] = {
    "_enc2_c2_point_Conv_output_0",
    "onnx__Mul_749",
    "onnx__Add_750"
  };
  uint32_t dimensions__enc2_c2_act_Relu_output_0[] = {1, 128, 128, 96};
  Qnn_Tensor_t outputs__enc2_c2_norm_Reshape_GroupNorm[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_enc2_c2_act_Relu_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0241159889847040f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__enc2_c2_act_Relu_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_enc2_c2_norm_Reshape_GroupNorm", // Node Name
                         "qti.aisw", // Package Name
                         "GroupNorm", // Qnn Node Type
                         params__enc2_c2_norm_Reshape_GroupNorm, // Node Params
                         2, // Num Node Params
                         inputs__enc2_c2_norm_Reshape_GroupNorm, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__enc2_c2_norm_Reshape_GroupNorm, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addNode__pool_1_AveragePool(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _pool_1_AveragePool */
  uint32_t dimensions___pool_1_AveragePool_filter_size[] = {2};
  uint32_t __pool_1_AveragePool_filter_size[] = {2, 2};
  uint32_t dimensions___pool_1_AveragePool_pad_amount[] = {2, 2};
  uint32_t __pool_1_AveragePool_pad_amount[] = {0, 0, 0, 0};
  uint32_t dimensions___pool_1_AveragePool_stride[] = {2};
  uint32_t __pool_1_AveragePool_stride[] = {2, 2};
  Qnn_Param_t params__pool_1_AveragePool[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="filter_size",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__pool_1_AveragePool_filter_size",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___pool_1_AveragePool_filter_size,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__pool_1_AveragePool_filter_size,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__pool_1_AveragePool_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___pool_1_AveragePool_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__pool_1_AveragePool_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__pool_1_AveragePool_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___pool_1_AveragePool_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__pool_1_AveragePool_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="count_pad_for_edges",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_BOOL_8, {.bool8Value = 1}}}}
  };
  const char*  inputs__pool_1_AveragePool[] = {
    "_enc2_c2_act_Relu_output_0"
  };
  uint32_t dimensions__pool_1_AveragePool_output_0[] = {1, 64, 64, 96};
  Qnn_Tensor_t outputs__pool_1_AveragePool[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_pool_1_AveragePool_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0143292667344213f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__pool_1_AveragePool_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_pool_1_AveragePool", // Node Name
                         "qti.aisw", // Package Name
                         "PoolAvg2d", // Qnn Node Type
                         params__pool_1_AveragePool, // Node Params
                         4, // Num Node Params
                         inputs__pool_1_AveragePool, // Input Tensor Names
                         1, // Num Input Tensor Names
                         outputs__pool_1_AveragePool, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_enc3_c1_depth_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_enc3_c1_depth_weight[] = {3, 3, 1, 96};
  VALIDATE(model.addTensor("enc3_c1_depth_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "enc3_c1_depth_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0028976893518120f, .offset= -128}}},
                                 .rank= 4,
                                 .dimensions=dimensions_enc3_c1_depth_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(enc3_c1_depth_weight),
                                                .dataSize=BINLEN(enc3_c1_depth_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__enc3_c1_depth_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__enc3_c1_depth_Conv_bias[] = {96};
  VALIDATE(model.addTensor("_enc3_c1_depth_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_enc3_c1_depth_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__enc3_c1_depth_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_enc3_c1_depth_Conv_bias),
                                                .dataSize=BINLEN(_enc3_c1_depth_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__enc3_c1_depth_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _enc3_c1_depth_Conv */
  uint32_t dimensions___enc3_c1_depth_Conv_dilation[] = {2};
  uint32_t __enc3_c1_depth_Conv_dilation[] = {1, 1};
  uint32_t dimensions___enc3_c1_depth_Conv_pad_amount[] = {2, 2};
  uint32_t __enc3_c1_depth_Conv_pad_amount[] = {1, 1, 1, 1};
  uint32_t dimensions___enc3_c1_depth_Conv_stride[] = {2};
  uint32_t __enc3_c1_depth_Conv_stride[] = {1, 1};
  Qnn_Param_t params__enc3_c1_depth_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc3_c1_depth_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___enc3_c1_depth_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc3_c1_depth_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc3_c1_depth_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___enc3_c1_depth_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc3_c1_depth_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc3_c1_depth_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___enc3_c1_depth_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc3_c1_depth_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}}
  };
  const char*  inputs__enc3_c1_depth_Conv[] = {
    "_pool_1_AveragePool_output_0",
    "enc3_c1_depth_weight",
    "_enc3_c1_depth_Conv_bias"
  };
  uint32_t dimensions__enc3_c1_depth_Conv_output_0[] = {1, 64, 64, 96};
  Qnn_Tensor_t outputs__enc3_c1_depth_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_enc3_c1_depth_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0140685662627220f, .offset= -150}}},
            .rank= 4,
            .dimensions=dimensions__enc3_c1_depth_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_enc3_c1_depth_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "DepthWiseConv2d", // Qnn Node Type
                         params__enc3_c1_depth_Conv, // Node Params
                         3, // Num Node Params
                         inputs__enc3_c1_depth_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__enc3_c1_depth_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_enc3_c1_point_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_enc3_c1_point_weight[] = {1, 1, 96, 192};
  VALIDATE(model.addTensor("enc3_c1_point_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "enc3_c1_point_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0018175896257162f, .offset= -119}}},
                                 .rank= 4,
                                 .dimensions=dimensions_enc3_c1_point_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(enc3_c1_point_weight),
                                                .dataSize=BINLEN(enc3_c1_point_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__enc3_c1_point_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__enc3_c1_point_Conv_bias[] = {192};
  VALIDATE(model.addTensor("_enc3_c1_point_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_enc3_c1_point_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__enc3_c1_point_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_enc3_c1_point_Conv_bias),
                                                .dataSize=BINLEN(_enc3_c1_point_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__enc3_c1_point_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _enc3_c1_point_Conv */
  uint32_t dimensions___enc3_c1_point_Conv_dilation[] = {2};
  uint32_t __enc3_c1_point_Conv_dilation[] = {1, 1};
  uint32_t dimensions___enc3_c1_point_Conv_pad_amount[] = {2, 2};
  uint32_t __enc3_c1_point_Conv_pad_amount[] = {0, 0, 0, 0};
  uint32_t dimensions___enc3_c1_point_Conv_stride[] = {2};
  uint32_t __enc3_c1_point_Conv_stride[] = {1, 1};
  Qnn_Param_t params__enc3_c1_point_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc3_c1_point_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___enc3_c1_point_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc3_c1_point_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc3_c1_point_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___enc3_c1_point_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc3_c1_point_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc3_c1_point_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___enc3_c1_point_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc3_c1_point_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 1}}}}
  };
  const char*  inputs__enc3_c1_point_Conv[] = {
    "_enc3_c1_depth_Conv_output_0",
    "enc3_c1_point_weight",
    "_enc3_c1_point_Conv_bias"
  };
  uint32_t dimensions__enc3_c1_point_Conv_output_0[] = {1, 64, 64, 192};
  Qnn_Tensor_t outputs__enc3_c1_point_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_enc3_c1_point_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0072369752451777f, .offset= -123}}},
            .rank= 4,
            .dimensions=dimensions__enc3_c1_point_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_enc3_c1_point_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "Conv2d", // Qnn Node Type
                         params__enc3_c1_point_Conv, // Node Params
                         4, // Num Node Params
                         inputs__enc3_c1_point_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__enc3_c1_point_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Mul_756(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Mul_756[] = {192};
  VALIDATE(model.addTensor("onnx__Mul_756", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Mul_756",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0042986753396690f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Mul_756,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Mul_756),
                                                .dataSize=BINLEN(onnx__Mul_756)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Add_757(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Add_757[] = {192};
  VALIDATE(model.addTensor("onnx__Add_757", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Add_757",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0005504873115569f, .offset= -140}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Add_757,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Add_757),
                                                .dataSize=BINLEN(onnx__Add_757)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__enc3_c1_norm_Reshape_GroupNorm(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _enc3_c1_norm_Reshape_GroupNorm */
  Qnn_Param_t params__enc3_c1_norm_Reshape_GroupNorm[] = {
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="epsilon",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_FLOAT_32, {.floatValue = 0.000010000000f}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 8}}}}
  };
  const char*  inputs__enc3_c1_norm_Reshape_GroupNorm[] = {
    "_enc3_c1_point_Conv_output_0",
    "onnx__Mul_756",
    "onnx__Add_757"
  };
  uint32_t dimensions__enc3_c1_act_Relu_output_0[] = {1, 64, 64, 192};
  Qnn_Tensor_t outputs__enc3_c1_norm_Reshape_GroupNorm[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_enc3_c1_act_Relu_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0196493845432997f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__enc3_c1_act_Relu_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_enc3_c1_norm_Reshape_GroupNorm", // Node Name
                         "qti.aisw", // Package Name
                         "GroupNorm", // Qnn Node Type
                         params__enc3_c1_norm_Reshape_GroupNorm, // Node Params
                         2, // Num Node Params
                         inputs__enc3_c1_norm_Reshape_GroupNorm, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__enc3_c1_norm_Reshape_GroupNorm, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_enc3_c2_depth_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_enc3_c2_depth_weight[] = {3, 3, 1, 192};
  VALIDATE(model.addTensor("enc3_c2_depth_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "enc3_c2_depth_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0029379345942289f, .offset= -128}}},
                                 .rank= 4,
                                 .dimensions=dimensions_enc3_c2_depth_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(enc3_c2_depth_weight),
                                                .dataSize=BINLEN(enc3_c2_depth_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__enc3_c2_depth_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__enc3_c2_depth_Conv_bias[] = {192};
  VALIDATE(model.addTensor("_enc3_c2_depth_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_enc3_c2_depth_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__enc3_c2_depth_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_enc3_c2_depth_Conv_bias),
                                                .dataSize=BINLEN(_enc3_c2_depth_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__enc3_c2_depth_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _enc3_c2_depth_Conv */
  uint32_t dimensions___enc3_c2_depth_Conv_dilation[] = {2};
  uint32_t __enc3_c2_depth_Conv_dilation[] = {1, 1};
  uint32_t dimensions___enc3_c2_depth_Conv_pad_amount[] = {2, 2};
  uint32_t __enc3_c2_depth_Conv_pad_amount[] = {1, 1, 1, 1};
  uint32_t dimensions___enc3_c2_depth_Conv_stride[] = {2};
  uint32_t __enc3_c2_depth_Conv_stride[] = {1, 1};
  Qnn_Param_t params__enc3_c2_depth_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc3_c2_depth_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___enc3_c2_depth_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc3_c2_depth_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc3_c2_depth_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___enc3_c2_depth_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc3_c2_depth_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc3_c2_depth_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___enc3_c2_depth_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc3_c2_depth_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}}
  };
  const char*  inputs__enc3_c2_depth_Conv[] = {
    "_enc3_c1_act_Relu_output_0",
    "enc3_c2_depth_weight",
    "_enc3_c2_depth_Conv_bias"
  };
  uint32_t dimensions__enc3_c2_depth_Conv_output_0[] = {1, 64, 64, 192};
  Qnn_Tensor_t outputs__enc3_c2_depth_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_enc3_c2_depth_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0228002555668354f, .offset= -149}}},
            .rank= 4,
            .dimensions=dimensions__enc3_c2_depth_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_enc3_c2_depth_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "DepthWiseConv2d", // Qnn Node Type
                         params__enc3_c2_depth_Conv, // Node Params
                         3, // Num Node Params
                         inputs__enc3_c2_depth_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__enc3_c2_depth_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_enc3_c2_point_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_enc3_c2_point_weight[] = {1, 1, 192, 192};
  VALIDATE(model.addTensor("enc3_c2_point_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "enc3_c2_point_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0018519684672356f, .offset= -145}}},
                                 .rank= 4,
                                 .dimensions=dimensions_enc3_c2_point_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(enc3_c2_point_weight),
                                                .dataSize=BINLEN(enc3_c2_point_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__enc3_c2_point_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__enc3_c2_point_Conv_bias[] = {192};
  VALIDATE(model.addTensor("_enc3_c2_point_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_enc3_c2_point_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__enc3_c2_point_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_enc3_c2_point_Conv_bias),
                                                .dataSize=BINLEN(_enc3_c2_point_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__enc3_c2_point_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _enc3_c2_point_Conv */
  uint32_t dimensions___enc3_c2_point_Conv_dilation[] = {2};
  uint32_t __enc3_c2_point_Conv_dilation[] = {1, 1};
  uint32_t dimensions___enc3_c2_point_Conv_pad_amount[] = {2, 2};
  uint32_t __enc3_c2_point_Conv_pad_amount[] = {0, 0, 0, 0};
  uint32_t dimensions___enc3_c2_point_Conv_stride[] = {2};
  uint32_t __enc3_c2_point_Conv_stride[] = {1, 1};
  Qnn_Param_t params__enc3_c2_point_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc3_c2_point_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___enc3_c2_point_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc3_c2_point_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc3_c2_point_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___enc3_c2_point_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc3_c2_point_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__enc3_c2_point_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___enc3_c2_point_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__enc3_c2_point_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 1}}}}
  };
  const char*  inputs__enc3_c2_point_Conv[] = {
    "_enc3_c2_depth_Conv_output_0",
    "enc3_c2_point_weight",
    "_enc3_c2_point_Conv_bias"
  };
  uint32_t dimensions__enc3_c2_point_Conv_output_0[] = {1, 64, 64, 192};
  Qnn_Tensor_t outputs__enc3_c2_point_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_enc3_c2_point_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0127337304875255f, .offset= -121}}},
            .rank= 4,
            .dimensions=dimensions__enc3_c2_point_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_enc3_c2_point_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "Conv2d", // Qnn Node Type
                         params__enc3_c2_point_Conv, // Node Params
                         4, // Num Node Params
                         inputs__enc3_c2_point_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__enc3_c2_point_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Mul_763(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Mul_763[] = {192};
  VALIDATE(model.addTensor("onnx__Mul_763", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Mul_763",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0042397226206958f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Mul_763,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Mul_763),
                                                .dataSize=BINLEN(onnx__Mul_763)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Add_764(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Add_764[] = {192};
  VALIDATE(model.addTensor("onnx__Add_764", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Add_764",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0005147953634150f, .offset= -205}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Add_764,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Add_764),
                                                .dataSize=BINLEN(onnx__Add_764)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__enc3_c2_norm_Reshape_GroupNorm(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _enc3_c2_norm_Reshape_GroupNorm */
  Qnn_Param_t params__enc3_c2_norm_Reshape_GroupNorm[] = {
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="epsilon",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_FLOAT_32, {.floatValue = 0.000010000000f}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 8}}}}
  };
  const char*  inputs__enc3_c2_norm_Reshape_GroupNorm[] = {
    "_enc3_c2_point_Conv_output_0",
    "onnx__Mul_763",
    "onnx__Add_764"
  };
  uint32_t dimensions__enc3_c2_act_Relu_output_0[] = {1, 64, 64, 192};
  Qnn_Tensor_t outputs__enc3_c2_norm_Reshape_GroupNorm[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_enc3_c2_act_Relu_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0198166016489267f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__enc3_c2_act_Relu_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_enc3_c2_norm_Reshape_GroupNorm", // Node Name
                         "qti.aisw", // Package Name
                         "GroupNorm", // Qnn Node Type
                         params__enc3_c2_norm_Reshape_GroupNorm, // Node Params
                         2, // Num Node Params
                         inputs__enc3_c2_norm_Reshape_GroupNorm, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__enc3_c2_norm_Reshape_GroupNorm, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addNode__pool_2_AveragePool(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _pool_2_AveragePool */
  uint32_t dimensions___pool_2_AveragePool_filter_size[] = {2};
  uint32_t __pool_2_AveragePool_filter_size[] = {2, 2};
  uint32_t dimensions___pool_2_AveragePool_pad_amount[] = {2, 2};
  uint32_t __pool_2_AveragePool_pad_amount[] = {0, 0, 0, 0};
  uint32_t dimensions___pool_2_AveragePool_stride[] = {2};
  uint32_t __pool_2_AveragePool_stride[] = {2, 2};
  Qnn_Param_t params__pool_2_AveragePool[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="filter_size",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__pool_2_AveragePool_filter_size",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___pool_2_AveragePool_filter_size,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__pool_2_AveragePool_filter_size,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__pool_2_AveragePool_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___pool_2_AveragePool_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__pool_2_AveragePool_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__pool_2_AveragePool_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___pool_2_AveragePool_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__pool_2_AveragePool_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="count_pad_for_edges",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_BOOL_8, {.bool8Value = 1}}}}
  };
  const char*  inputs__pool_2_AveragePool[] = {
    "_enc3_c2_act_Relu_output_0"
  };
  uint32_t dimensions__pool_2_AveragePool_output_0[] = {1, 32, 32, 192};
  Qnn_Tensor_t outputs__pool_2_AveragePool[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_pool_2_AveragePool_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0157842077314854f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__pool_2_AveragePool_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_pool_2_AveragePool", // Node Name
                         "qti.aisw", // Package Name
                         "PoolAvg2d", // Qnn Node Type
                         params__pool_2_AveragePool, // Node Params
                         4, // Num Node Params
                         inputs__pool_2_AveragePool, // Input Tensor Names
                         1, // Num Input Tensor Names
                         outputs__pool_2_AveragePool, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_bottleneck_c1_depth_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_bottleneck_c1_depth_weight[] = {3, 3, 1, 192};
  VALIDATE(model.addTensor("bottleneck_c1_depth_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "bottleneck_c1_depth_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0030648689717054f, .offset= -125}}},
                                 .rank= 4,
                                 .dimensions=dimensions_bottleneck_c1_depth_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(bottleneck_c1_depth_weight),
                                                .dataSize=BINLEN(bottleneck_c1_depth_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__bottleneck_c1_depth_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__bottleneck_c1_depth_Conv_bias[] = {192};
  VALIDATE(model.addTensor("_bottleneck_c1_depth_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_bottleneck_c1_depth_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__bottleneck_c1_depth_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_bottleneck_c1_depth_Conv_bias),
                                                .dataSize=BINLEN(_bottleneck_c1_depth_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__bottleneck_c1_depth_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _bottleneck_c1_depth_Conv */
  uint32_t dimensions___bottleneck_c1_depth_Conv_dilation[] = {2};
  uint32_t __bottleneck_c1_depth_Conv_dilation[] = {1, 1};
  uint32_t dimensions___bottleneck_c1_depth_Conv_pad_amount[] = {2, 2};
  uint32_t __bottleneck_c1_depth_Conv_pad_amount[] = {1, 1, 1, 1};
  uint32_t dimensions___bottleneck_c1_depth_Conv_stride[] = {2};
  uint32_t __bottleneck_c1_depth_Conv_stride[] = {1, 1};
  Qnn_Param_t params__bottleneck_c1_depth_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__bottleneck_c1_depth_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___bottleneck_c1_depth_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__bottleneck_c1_depth_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__bottleneck_c1_depth_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___bottleneck_c1_depth_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__bottleneck_c1_depth_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__bottleneck_c1_depth_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___bottleneck_c1_depth_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__bottleneck_c1_depth_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}}
  };
  const char*  inputs__bottleneck_c1_depth_Conv[] = {
    "_pool_2_AveragePool_output_0",
    "bottleneck_c1_depth_weight",
    "_bottleneck_c1_depth_Conv_bias"
  };
  uint32_t dimensions__bottleneck_c1_depth_Conv_output_0[] = {1, 32, 32, 192};
  Qnn_Tensor_t outputs__bottleneck_c1_depth_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_bottleneck_c1_depth_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0130228791385889f, .offset= -117}}},
            .rank= 4,
            .dimensions=dimensions__bottleneck_c1_depth_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_bottleneck_c1_depth_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "DepthWiseConv2d", // Qnn Node Type
                         params__bottleneck_c1_depth_Conv, // Node Params
                         3, // Num Node Params
                         inputs__bottleneck_c1_depth_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__bottleneck_c1_depth_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_bottleneck_c1_point_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_bottleneck_c1_point_weight[] = {1, 1, 192, 384};
  VALIDATE(model.addTensor("bottleneck_c1_point_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "bottleneck_c1_point_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0019570721779019f, .offset= -134}}},
                                 .rank= 4,
                                 .dimensions=dimensions_bottleneck_c1_point_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(bottleneck_c1_point_weight),
                                                .dataSize=BINLEN(bottleneck_c1_point_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__bottleneck_c1_point_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__bottleneck_c1_point_Conv_bias[] = {384};
  VALIDATE(model.addTensor("_bottleneck_c1_point_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_bottleneck_c1_point_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__bottleneck_c1_point_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_bottleneck_c1_point_Conv_bias),
                                                .dataSize=BINLEN(_bottleneck_c1_point_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__bottleneck_c1_point_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _bottleneck_c1_point_Conv */
  uint32_t dimensions___bottleneck_c1_point_Conv_dilation[] = {2};
  uint32_t __bottleneck_c1_point_Conv_dilation[] = {1, 1};
  uint32_t dimensions___bottleneck_c1_point_Conv_pad_amount[] = {2, 2};
  uint32_t __bottleneck_c1_point_Conv_pad_amount[] = {0, 0, 0, 0};
  uint32_t dimensions___bottleneck_c1_point_Conv_stride[] = {2};
  uint32_t __bottleneck_c1_point_Conv_stride[] = {1, 1};
  Qnn_Param_t params__bottleneck_c1_point_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__bottleneck_c1_point_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___bottleneck_c1_point_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__bottleneck_c1_point_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__bottleneck_c1_point_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___bottleneck_c1_point_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__bottleneck_c1_point_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__bottleneck_c1_point_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___bottleneck_c1_point_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__bottleneck_c1_point_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 1}}}}
  };
  const char*  inputs__bottleneck_c1_point_Conv[] = {
    "_bottleneck_c1_depth_Conv_output_0",
    "bottleneck_c1_point_weight",
    "_bottleneck_c1_point_Conv_bias"
  };
  uint32_t dimensions__bottleneck_c1_point_Conv_output_0[] = {1, 32, 32, 384};
  Qnn_Tensor_t outputs__bottleneck_c1_point_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_bottleneck_c1_point_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0083428472280502f, .offset= -131}}},
            .rank= 4,
            .dimensions=dimensions__bottleneck_c1_point_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_bottleneck_c1_point_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "Conv2d", // Qnn Node Type
                         params__bottleneck_c1_point_Conv, // Node Params
                         4, // Num Node Params
                         inputs__bottleneck_c1_point_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__bottleneck_c1_point_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Mul_770(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Mul_770[] = {384};
  VALIDATE(model.addTensor("onnx__Mul_770", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Mul_770",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0044945804402232f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Mul_770,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Mul_770),
                                                .dataSize=BINLEN(onnx__Mul_770)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Add_771(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Add_771[] = {384};
  VALIDATE(model.addTensor("onnx__Add_771", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Add_771",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0006676407647319f, .offset= -161}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Add_771,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Add_771),
                                                .dataSize=BINLEN(onnx__Add_771)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__bottleneck_c1_norm_Reshape_GroupNorm(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _bottleneck_c1_norm_Reshape_GroupNorm */
  Qnn_Param_t params__bottleneck_c1_norm_Reshape_GroupNorm[] = {
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="epsilon",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_FLOAT_32, {.floatValue = 0.000010000000f}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 8}}}}
  };
  const char*  inputs__bottleneck_c1_norm_Reshape_GroupNorm[] = {
    "_bottleneck_c1_point_Conv_output_0",
    "onnx__Mul_770",
    "onnx__Add_771"
  };
  uint32_t dimensions__bottleneck_c1_act_Relu_output_0[] = {1, 32, 32, 384};
  Qnn_Tensor_t outputs__bottleneck_c1_norm_Reshape_GroupNorm[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_bottleneck_c1_act_Relu_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0203463584184647f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__bottleneck_c1_act_Relu_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_bottleneck_c1_norm_Reshape_GroupNorm", // Node Name
                         "qti.aisw", // Package Name
                         "GroupNorm", // Qnn Node Type
                         params__bottleneck_c1_norm_Reshape_GroupNorm, // Node Params
                         2, // Num Node Params
                         inputs__bottleneck_c1_norm_Reshape_GroupNorm, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__bottleneck_c1_norm_Reshape_GroupNorm, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_bottleneck_c2_depth_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_bottleneck_c2_depth_weight[] = {3, 3, 1, 384};
  VALIDATE(model.addTensor("bottleneck_c2_depth_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "bottleneck_c2_depth_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0029862653464079f, .offset= -126}}},
                                 .rank= 4,
                                 .dimensions=dimensions_bottleneck_c2_depth_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(bottleneck_c2_depth_weight),
                                                .dataSize=BINLEN(bottleneck_c2_depth_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__bottleneck_c2_depth_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__bottleneck_c2_depth_Conv_bias[] = {384};
  VALIDATE(model.addTensor("_bottleneck_c2_depth_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_bottleneck_c2_depth_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__bottleneck_c2_depth_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_bottleneck_c2_depth_Conv_bias),
                                                .dataSize=BINLEN(_bottleneck_c2_depth_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__bottleneck_c2_depth_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _bottleneck_c2_depth_Conv */
  uint32_t dimensions___bottleneck_c2_depth_Conv_dilation[] = {2};
  uint32_t __bottleneck_c2_depth_Conv_dilation[] = {1, 1};
  uint32_t dimensions___bottleneck_c2_depth_Conv_pad_amount[] = {2, 2};
  uint32_t __bottleneck_c2_depth_Conv_pad_amount[] = {1, 1, 1, 1};
  uint32_t dimensions___bottleneck_c2_depth_Conv_stride[] = {2};
  uint32_t __bottleneck_c2_depth_Conv_stride[] = {1, 1};
  Qnn_Param_t params__bottleneck_c2_depth_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__bottleneck_c2_depth_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___bottleneck_c2_depth_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__bottleneck_c2_depth_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__bottleneck_c2_depth_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___bottleneck_c2_depth_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__bottleneck_c2_depth_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__bottleneck_c2_depth_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___bottleneck_c2_depth_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__bottleneck_c2_depth_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}}
  };
  const char*  inputs__bottleneck_c2_depth_Conv[] = {
    "_bottleneck_c1_act_Relu_output_0",
    "bottleneck_c2_depth_weight",
    "_bottleneck_c2_depth_Conv_bias"
  };
  uint32_t dimensions__bottleneck_c2_depth_Conv_output_0[] = {1, 32, 32, 384};
  Qnn_Tensor_t outputs__bottleneck_c2_depth_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_bottleneck_c2_depth_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0245190616697073f, .offset= -134}}},
            .rank= 4,
            .dimensions=dimensions__bottleneck_c2_depth_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_bottleneck_c2_depth_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "DepthWiseConv2d", // Qnn Node Type
                         params__bottleneck_c2_depth_Conv, // Node Params
                         3, // Num Node Params
                         inputs__bottleneck_c2_depth_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__bottleneck_c2_depth_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_bottleneck_c2_point_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_bottleneck_c2_point_weight[] = {1, 1, 384, 384};
  VALIDATE(model.addTensor("bottleneck_c2_point_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "bottleneck_c2_point_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0015724098775536f, .offset= -138}}},
                                 .rank= 4,
                                 .dimensions=dimensions_bottleneck_c2_point_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(bottleneck_c2_point_weight),
                                                .dataSize=BINLEN(bottleneck_c2_point_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__bottleneck_c2_point_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__bottleneck_c2_point_Conv_bias[] = {384};
  VALIDATE(model.addTensor("_bottleneck_c2_point_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_bottleneck_c2_point_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__bottleneck_c2_point_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_bottleneck_c2_point_Conv_bias),
                                                .dataSize=BINLEN(_bottleneck_c2_point_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__bottleneck_c2_point_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _bottleneck_c2_point_Conv */
  uint32_t dimensions___bottleneck_c2_point_Conv_dilation[] = {2};
  uint32_t __bottleneck_c2_point_Conv_dilation[] = {1, 1};
  uint32_t dimensions___bottleneck_c2_point_Conv_pad_amount[] = {2, 2};
  uint32_t __bottleneck_c2_point_Conv_pad_amount[] = {0, 0, 0, 0};
  uint32_t dimensions___bottleneck_c2_point_Conv_stride[] = {2};
  uint32_t __bottleneck_c2_point_Conv_stride[] = {1, 1};
  Qnn_Param_t params__bottleneck_c2_point_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__bottleneck_c2_point_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___bottleneck_c2_point_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__bottleneck_c2_point_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__bottleneck_c2_point_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___bottleneck_c2_point_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__bottleneck_c2_point_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__bottleneck_c2_point_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___bottleneck_c2_point_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__bottleneck_c2_point_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 1}}}}
  };
  const char*  inputs__bottleneck_c2_point_Conv[] = {
    "_bottleneck_c2_depth_Conv_output_0",
    "bottleneck_c2_point_weight",
    "_bottleneck_c2_point_Conv_bias"
  };
  uint32_t dimensions__bottleneck_c2_point_Conv_output_0[] = {1, 32, 32, 384};
  Qnn_Tensor_t outputs__bottleneck_c2_point_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_bottleneck_c2_point_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0149265304207802f, .offset= -139}}},
            .rank= 4,
            .dimensions=dimensions__bottleneck_c2_point_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_bottleneck_c2_point_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "Conv2d", // Qnn Node Type
                         params__bottleneck_c2_point_Conv, // Node Params
                         4, // Num Node Params
                         inputs__bottleneck_c2_point_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__bottleneck_c2_point_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Mul_777(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Mul_777[] = {384};
  VALIDATE(model.addTensor("onnx__Mul_777", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Mul_777",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0043543875217438f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Mul_777,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Mul_777),
                                                .dataSize=BINLEN(onnx__Mul_777)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Add_778(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Add_778[] = {384};
  VALIDATE(model.addTensor("onnx__Add_778", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Add_778",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0006138059543446f, .offset= -231}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Add_778,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Add_778),
                                                .dataSize=BINLEN(onnx__Add_778)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__bottleneck_c2_norm_Reshape_GroupNorm(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _bottleneck_c2_norm_Reshape_GroupNorm */
  Qnn_Param_t params__bottleneck_c2_norm_Reshape_GroupNorm[] = {
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="epsilon",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_FLOAT_32, {.floatValue = 0.000010000000f}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 8}}}}
  };
  const char*  inputs__bottleneck_c2_norm_Reshape_GroupNorm[] = {
    "_bottleneck_c2_point_Conv_output_0",
    "onnx__Mul_777",
    "onnx__Add_778"
  };
  uint32_t dimensions__bottleneck_c2_act_Relu_output_0[] = {1, 32, 32, 384};
  Qnn_Tensor_t outputs__bottleneck_c2_norm_Reshape_GroupNorm[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_bottleneck_c2_act_Relu_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0295761153101921f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__bottleneck_c2_act_Relu_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_bottleneck_c2_norm_Reshape_GroupNorm", // Node Name
                         "qti.aisw", // Package Name
                         "GroupNorm", // Qnn Node Type
                         params__bottleneck_c2_norm_Reshape_GroupNorm, // Node Params
                         2, // Num Node Params
                         inputs__bottleneck_c2_norm_Reshape_GroupNorm, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__bottleneck_c2_norm_Reshape_GroupNorm, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Conv_709(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Conv_709[] = {3, 3, 384, 96};
  VALIDATE(model.addTensor("onnx__Conv_709", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Conv_709",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0003287107101642f, .offset= -121}}},
                                 .rank= 4,
                                 .dimensions=dimensions_onnx__Conv_709,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Conv_709),
                                                .dataSize=BINLEN(onnx__Conv_709)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Conv_710(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Conv_710[] = {96};
  VALIDATE(model.addTensor("onnx__Conv_710", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Conv_710",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0125380465760827f, .offset= -125}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Conv_710,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Conv_710),
                                                .dataSize=BINLEN(onnx__Conv_710)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__aspp_branches_0_branches_0_0_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _aspp_branches_0_branches_0_0_Conv */
  uint32_t dimensions___aspp_branches_0_branches_0_0_Conv_dilation[] = {2};
  uint32_t __aspp_branches_0_branches_0_0_Conv_dilation[] = {1, 1};
  uint32_t dimensions___aspp_branches_0_branches_0_0_Conv_pad_amount[] = {2, 2};
  uint32_t __aspp_branches_0_branches_0_0_Conv_pad_amount[] = {1, 1, 1, 1};
  uint32_t dimensions___aspp_branches_0_branches_0_0_Conv_stride[] = {2};
  uint32_t __aspp_branches_0_branches_0_0_Conv_stride[] = {1, 1};
  Qnn_Param_t params__aspp_branches_0_branches_0_0_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__aspp_branches_0_branches_0_0_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___aspp_branches_0_branches_0_0_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__aspp_branches_0_branches_0_0_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__aspp_branches_0_branches_0_0_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___aspp_branches_0_branches_0_0_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__aspp_branches_0_branches_0_0_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__aspp_branches_0_branches_0_0_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___aspp_branches_0_branches_0_0_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__aspp_branches_0_branches_0_0_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 1}}}}
  };
  const char*  inputs__aspp_branches_0_branches_0_0_Conv[] = {
    "_bottleneck_c2_act_Relu_output_0",
    "onnx__Conv_709",
    "onnx__Conv_710"
  };
  uint32_t dimensions__aspp_branches_0_branches_0_2_Relu_output_0[] = {1, 32, 32, 96};
  Qnn_Tensor_t outputs__aspp_branches_0_branches_0_0_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_aspp_branches_0_branches_0_2_Relu_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0125009249895811f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__aspp_branches_0_branches_0_2_Relu_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_aspp_branches_0_branches_0_0_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "Conv2d", // Qnn Node Type
                         params__aspp_branches_0_branches_0_0_Conv, // Node Params
                         4, // Num Node Params
                         inputs__aspp_branches_0_branches_0_0_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__aspp_branches_0_branches_0_0_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Conv_712(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Conv_712[] = {3, 3, 384, 96};
  VALIDATE(model.addTensor("onnx__Conv_712", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Conv_712",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0004572789184749f, .offset= -127}}},
                                 .rank= 4,
                                 .dimensions=dimensions_onnx__Conv_712,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Conv_712),
                                                .dataSize=BINLEN(onnx__Conv_712)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Conv_713(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Conv_713[] = {96};
  VALIDATE(model.addTensor("onnx__Conv_713", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Conv_713",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0134608512744308f, .offset= -134}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Conv_713,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Conv_713),
                                                .dataSize=BINLEN(onnx__Conv_713)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__aspp_branches_1_branches_1_0_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _aspp_branches_1_branches_1_0_Conv */
  uint32_t dimensions___aspp_branches_1_branches_1_0_Conv_dilation[] = {2};
  uint32_t __aspp_branches_1_branches_1_0_Conv_dilation[] = {2, 2};
  uint32_t dimensions___aspp_branches_1_branches_1_0_Conv_pad_amount[] = {2, 2};
  uint32_t __aspp_branches_1_branches_1_0_Conv_pad_amount[] = {2, 2, 2, 2};
  uint32_t dimensions___aspp_branches_1_branches_1_0_Conv_stride[] = {2};
  uint32_t __aspp_branches_1_branches_1_0_Conv_stride[] = {1, 1};
  Qnn_Param_t params__aspp_branches_1_branches_1_0_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__aspp_branches_1_branches_1_0_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___aspp_branches_1_branches_1_0_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__aspp_branches_1_branches_1_0_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__aspp_branches_1_branches_1_0_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___aspp_branches_1_branches_1_0_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__aspp_branches_1_branches_1_0_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__aspp_branches_1_branches_1_0_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___aspp_branches_1_branches_1_0_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__aspp_branches_1_branches_1_0_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 1}}}}
  };
  const char*  inputs__aspp_branches_1_branches_1_0_Conv[] = {
    "_bottleneck_c2_act_Relu_output_0",
    "onnx__Conv_712",
    "onnx__Conv_713"
  };
  uint32_t dimensions__aspp_branches_1_branches_1_2_Relu_output_0[] = {1, 32, 32, 96};
  Qnn_Tensor_t outputs__aspp_branches_1_branches_1_0_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_aspp_branches_1_branches_1_2_Relu_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0137738734483719f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__aspp_branches_1_branches_1_2_Relu_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_aspp_branches_1_branches_1_0_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "Conv2d", // Qnn Node Type
                         params__aspp_branches_1_branches_1_0_Conv, // Node Params
                         4, // Num Node Params
                         inputs__aspp_branches_1_branches_1_0_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__aspp_branches_1_branches_1_0_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Conv_715(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Conv_715[] = {3, 3, 384, 96};
  VALIDATE(model.addTensor("onnx__Conv_715", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Conv_715",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0006239345530048f, .offset= -119}}},
                                 .rank= 4,
                                 .dimensions=dimensions_onnx__Conv_715,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Conv_715),
                                                .dataSize=BINLEN(onnx__Conv_715)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Conv_716(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Conv_716[] = {96};
  VALIDATE(model.addTensor("onnx__Conv_716", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Conv_716",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0133287142962217f, .offset= -125}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Conv_716,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Conv_716),
                                                .dataSize=BINLEN(onnx__Conv_716)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__aspp_branches_2_branches_2_0_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _aspp_branches_2_branches_2_0_Conv */
  uint32_t dimensions___aspp_branches_2_branches_2_0_Conv_dilation[] = {2};
  uint32_t __aspp_branches_2_branches_2_0_Conv_dilation[] = {4, 4};
  uint32_t dimensions___aspp_branches_2_branches_2_0_Conv_pad_amount[] = {2, 2};
  uint32_t __aspp_branches_2_branches_2_0_Conv_pad_amount[] = {4, 4, 4, 4};
  uint32_t dimensions___aspp_branches_2_branches_2_0_Conv_stride[] = {2};
  uint32_t __aspp_branches_2_branches_2_0_Conv_stride[] = {1, 1};
  Qnn_Param_t params__aspp_branches_2_branches_2_0_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__aspp_branches_2_branches_2_0_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___aspp_branches_2_branches_2_0_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__aspp_branches_2_branches_2_0_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__aspp_branches_2_branches_2_0_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___aspp_branches_2_branches_2_0_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__aspp_branches_2_branches_2_0_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__aspp_branches_2_branches_2_0_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___aspp_branches_2_branches_2_0_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__aspp_branches_2_branches_2_0_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 1}}}}
  };
  const char*  inputs__aspp_branches_2_branches_2_0_Conv[] = {
    "_bottleneck_c2_act_Relu_output_0",
    "onnx__Conv_715",
    "onnx__Conv_716"
  };
  uint32_t dimensions__aspp_branches_2_branches_2_2_Relu_output_0[] = {1, 32, 32, 96};
  Qnn_Tensor_t outputs__aspp_branches_2_branches_2_0_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_aspp_branches_2_branches_2_2_Relu_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0136616043746471f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__aspp_branches_2_branches_2_2_Relu_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_aspp_branches_2_branches_2_0_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "Conv2d", // Qnn Node Type
                         params__aspp_branches_2_branches_2_0_Conv, // Node Params
                         4, // Num Node Params
                         inputs__aspp_branches_2_branches_2_0_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__aspp_branches_2_branches_2_0_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Conv_718(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Conv_718[] = {3, 3, 384, 96};
  VALIDATE(model.addTensor("onnx__Conv_718", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Conv_718",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0006015891558491f, .offset= -125}}},
                                 .rank= 4,
                                 .dimensions=dimensions_onnx__Conv_718,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Conv_718),
                                                .dataSize=BINLEN(onnx__Conv_718)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Conv_719(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Conv_719[] = {96};
  VALIDATE(model.addTensor("onnx__Conv_719", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Conv_719",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0156898349523544f, .offset= -139}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Conv_719,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Conv_719),
                                                .dataSize=BINLEN(onnx__Conv_719)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__aspp_branches_3_branches_3_0_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _aspp_branches_3_branches_3_0_Conv */
  uint32_t dimensions___aspp_branches_3_branches_3_0_Conv_dilation[] = {2};
  uint32_t __aspp_branches_3_branches_3_0_Conv_dilation[] = {8, 8};
  uint32_t dimensions___aspp_branches_3_branches_3_0_Conv_pad_amount[] = {2, 2};
  uint32_t __aspp_branches_3_branches_3_0_Conv_pad_amount[] = {8, 8, 8, 8};
  uint32_t dimensions___aspp_branches_3_branches_3_0_Conv_stride[] = {2};
  uint32_t __aspp_branches_3_branches_3_0_Conv_stride[] = {1, 1};
  Qnn_Param_t params__aspp_branches_3_branches_3_0_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__aspp_branches_3_branches_3_0_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___aspp_branches_3_branches_3_0_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__aspp_branches_3_branches_3_0_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__aspp_branches_3_branches_3_0_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___aspp_branches_3_branches_3_0_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__aspp_branches_3_branches_3_0_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__aspp_branches_3_branches_3_0_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___aspp_branches_3_branches_3_0_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__aspp_branches_3_branches_3_0_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 1}}}}
  };
  const char*  inputs__aspp_branches_3_branches_3_0_Conv[] = {
    "_bottleneck_c2_act_Relu_output_0",
    "onnx__Conv_718",
    "onnx__Conv_719"
  };
  uint32_t dimensions__aspp_branches_3_branches_3_2_Relu_output_0[] = {1, 32, 32, 96};
  Qnn_Tensor_t outputs__aspp_branches_3_branches_3_0_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_aspp_branches_3_branches_3_2_Relu_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0144074847921729f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__aspp_branches_3_branches_3_2_Relu_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_aspp_branches_3_branches_3_0_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "Conv2d", // Qnn Node Type
                         params__aspp_branches_3_branches_3_0_Conv, // Node Params
                         4, // Num Node Params
                         inputs__aspp_branches_3_branches_3_0_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__aspp_branches_3_branches_3_0_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addNode__aspp_Concat(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _aspp_Concat */
  Qnn_Param_t params__aspp_Concat[] = {
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="axis",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 3}}}}
  };
  const char*  inputs__aspp_Concat[] = {
    "_aspp_branches_0_branches_0_2_Relu_output_0",
    "_aspp_branches_1_branches_1_2_Relu_output_0",
    "_aspp_branches_2_branches_2_2_Relu_output_0",
    "_aspp_branches_3_branches_3_2_Relu_output_0"
  };
  uint32_t dimensions__aspp_Concat_output_0[] = {1, 32, 32, 384};
  Qnn_Tensor_t outputs__aspp_Concat[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_aspp_Concat_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0144074847921729f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__aspp_Concat_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_aspp_Concat", // Node Name
                         "qti.aisw", // Package Name
                         "Concat", // Qnn Node Type
                         params__aspp_Concat, // Node Params
                         1, // Num Node Params
                         inputs__aspp_Concat, // Input Tensor Names
                         4, // Num Input Tensor Names
                         outputs__aspp_Concat, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Conv_721(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Conv_721[] = {1, 1, 384, 384};
  VALIDATE(model.addTensor("onnx__Conv_721", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Conv_721",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0019738299306482f, .offset= -136}}},
                                 .rank= 4,
                                 .dimensions=dimensions_onnx__Conv_721,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Conv_721),
                                                .dataSize=BINLEN(onnx__Conv_721)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Conv_722(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Conv_722[] = {384};
  VALIDATE(model.addTensor("onnx__Conv_722", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Conv_722",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0147486804053187f, .offset= -143}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Conv_722,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Conv_722),
                                                .dataSize=BINLEN(onnx__Conv_722)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__aspp_proj_proj_0_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _aspp_proj_proj_0_Conv */
  uint32_t dimensions___aspp_proj_proj_0_Conv_dilation[] = {2};
  uint32_t __aspp_proj_proj_0_Conv_dilation[] = {1, 1};
  uint32_t dimensions___aspp_proj_proj_0_Conv_pad_amount[] = {2, 2};
  uint32_t __aspp_proj_proj_0_Conv_pad_amount[] = {0, 0, 0, 0};
  uint32_t dimensions___aspp_proj_proj_0_Conv_stride[] = {2};
  uint32_t __aspp_proj_proj_0_Conv_stride[] = {1, 1};
  Qnn_Param_t params__aspp_proj_proj_0_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__aspp_proj_proj_0_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___aspp_proj_proj_0_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__aspp_proj_proj_0_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__aspp_proj_proj_0_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___aspp_proj_proj_0_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__aspp_proj_proj_0_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__aspp_proj_proj_0_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___aspp_proj_proj_0_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__aspp_proj_proj_0_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 1}}}}
  };
  const char*  inputs__aspp_proj_proj_0_Conv[] = {
    "_aspp_Concat_output_0",
    "onnx__Conv_721",
    "onnx__Conv_722"
  };
  uint32_t dimensions__aspp_proj_proj_2_Relu_output_0[] = {1, 32, 32, 384};
  Qnn_Tensor_t outputs__aspp_proj_proj_0_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_aspp_proj_proj_2_Relu_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0181920770555735f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__aspp_proj_proj_2_Relu_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_aspp_proj_proj_0_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "Conv2d", // Qnn Node Type
                         params__aspp_proj_proj_0_Conv, // Node Params
                         4, // Num Node Params
                         inputs__aspp_proj_proj_0_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__aspp_proj_proj_0_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addNode__Resize(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _Resize */
  Qnn_Param_t params__Resize[] = {
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="align_corners",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_BOOL_8, {.bool8Value = 0}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="antialias",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_BOOL_8, {.bool8Value = 0}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="half_pixel_centers",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_BOOL_8, {.bool8Value = 1}}}}
  };
  const char*  inputs__Resize[] = {
    "_aspp_proj_proj_2_Relu_output_0"
  };
  uint32_t dimensions__Resize_output_0[] = {1, 64, 64, 384};
  Qnn_Tensor_t outputs__Resize[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_Resize_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0181920770555735f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__Resize_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_Resize", // Node Name
                         "qti.aisw", // Package Name
                         "ResizeBilinear", // Qnn Node Type
                         params__Resize, // Node Params
                         3, // Num Node Params
                         inputs__Resize, // Input Tensor Names
                         1, // Num Input Tensor Names
                         outputs__Resize, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addNode__Concat_2(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _Concat_2 */
  Qnn_Param_t params__Concat_2[] = {
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="axis",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 3}}}}
  };
  const char*  inputs__Concat_2[] = {
    "_Resize_output_0",
    "_enc3_c2_act_Relu_output_0"
  };
  uint32_t dimensions__Concat_2_output_0[] = {1, 64, 64, 576};
  Qnn_Tensor_t outputs__Concat_2[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_Concat_2_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0198166016489267f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__Concat_2_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_Concat_2", // Node Name
                         "qti.aisw", // Package Name
                         "Concat", // Qnn Node Type
                         params__Concat_2, // Node Params
                         1, // Num Node Params
                         inputs__Concat_2, // Input Tensor Names
                         2, // Num Input Tensor Names
                         outputs__Concat_2, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_dec3_c1_depth_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_dec3_c1_depth_weight[] = {3, 3, 1, 576};
  VALIDATE(model.addTensor("dec3_c1_depth_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "dec3_c1_depth_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0031427484937012f, .offset= -130}}},
                                 .rank= 4,
                                 .dimensions=dimensions_dec3_c1_depth_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(dec3_c1_depth_weight),
                                                .dataSize=BINLEN(dec3_c1_depth_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__dec3_c1_depth_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__dec3_c1_depth_Conv_bias[] = {576};
  VALIDATE(model.addTensor("_dec3_c1_depth_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_dec3_c1_depth_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__dec3_c1_depth_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_dec3_c1_depth_Conv_bias),
                                                .dataSize=BINLEN(_dec3_c1_depth_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__dec3_c1_depth_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _dec3_c1_depth_Conv */
  uint32_t dimensions___dec3_c1_depth_Conv_dilation[] = {2};
  uint32_t __dec3_c1_depth_Conv_dilation[] = {1, 1};
  uint32_t dimensions___dec3_c1_depth_Conv_pad_amount[] = {2, 2};
  uint32_t __dec3_c1_depth_Conv_pad_amount[] = {1, 1, 1, 1};
  uint32_t dimensions___dec3_c1_depth_Conv_stride[] = {2};
  uint32_t __dec3_c1_depth_Conv_stride[] = {1, 1};
  Qnn_Param_t params__dec3_c1_depth_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec3_c1_depth_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___dec3_c1_depth_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec3_c1_depth_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec3_c1_depth_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___dec3_c1_depth_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec3_c1_depth_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec3_c1_depth_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___dec3_c1_depth_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec3_c1_depth_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}}
  };
  const char*  inputs__dec3_c1_depth_Conv[] = {
    "_Concat_2_output_0",
    "dec3_c1_depth_weight",
    "_dec3_c1_depth_Conv_bias"
  };
  uint32_t dimensions__dec3_c1_depth_Conv_output_0[] = {1, 64, 64, 576};
  Qnn_Tensor_t outputs__dec3_c1_depth_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_dec3_c1_depth_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0370363332331181f, .offset= -108}}},
            .rank= 4,
            .dimensions=dimensions__dec3_c1_depth_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_dec3_c1_depth_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "DepthWiseConv2d", // Qnn Node Type
                         params__dec3_c1_depth_Conv, // Node Params
                         3, // Num Node Params
                         inputs__dec3_c1_depth_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__dec3_c1_depth_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_dec3_c1_point_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_dec3_c1_point_weight[] = {1, 1, 576, 192};
  VALIDATE(model.addTensor("dec3_c1_point_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "dec3_c1_point_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0033074012026191f, .offset= -124}}},
                                 .rank= 4,
                                 .dimensions=dimensions_dec3_c1_point_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(dec3_c1_point_weight),
                                                .dataSize=BINLEN(dec3_c1_point_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__dec3_c1_point_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__dec3_c1_point_Conv_bias[] = {192};
  VALIDATE(model.addTensor("_dec3_c1_point_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_dec3_c1_point_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__dec3_c1_point_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_dec3_c1_point_Conv_bias),
                                                .dataSize=BINLEN(_dec3_c1_point_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__dec3_c1_point_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _dec3_c1_point_Conv */
  uint32_t dimensions___dec3_c1_point_Conv_dilation[] = {2};
  uint32_t __dec3_c1_point_Conv_dilation[] = {1, 1};
  uint32_t dimensions___dec3_c1_point_Conv_pad_amount[] = {2, 2};
  uint32_t __dec3_c1_point_Conv_pad_amount[] = {0, 0, 0, 0};
  uint32_t dimensions___dec3_c1_point_Conv_stride[] = {2};
  uint32_t __dec3_c1_point_Conv_stride[] = {1, 1};
  Qnn_Param_t params__dec3_c1_point_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec3_c1_point_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___dec3_c1_point_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec3_c1_point_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec3_c1_point_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___dec3_c1_point_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec3_c1_point_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec3_c1_point_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___dec3_c1_point_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec3_c1_point_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 1}}}}
  };
  const char*  inputs__dec3_c1_point_Conv[] = {
    "_dec3_c1_depth_Conv_output_0",
    "dec3_c1_point_weight",
    "_dec3_c1_point_Conv_bias"
  };
  uint32_t dimensions__dec3_c1_point_Conv_output_0[] = {1, 64, 64, 192};
  Qnn_Tensor_t outputs__dec3_c1_point_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_dec3_c1_point_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0318340547382832f, .offset= -157}}},
            .rank= 4,
            .dimensions=dimensions__dec3_c1_point_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_dec3_c1_point_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "Conv2d", // Qnn Node Type
                         params__dec3_c1_point_Conv, // Node Params
                         4, // Num Node Params
                         inputs__dec3_c1_point_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__dec3_c1_point_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Mul_784(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Mul_784[] = {192};
  VALIDATE(model.addTensor("onnx__Mul_784", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Mul_784",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0044008712284267f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Mul_784,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Mul_784),
                                                .dataSize=BINLEN(onnx__Mul_784)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Add_785(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Add_785[] = {192};
  VALIDATE(model.addTensor("onnx__Add_785", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Add_785",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0005860311794095f, .offset= -188}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Add_785,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Add_785),
                                                .dataSize=BINLEN(onnx__Add_785)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__dec3_c1_norm_Reshape_GroupNorm(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _dec3_c1_norm_Reshape_GroupNorm */
  Qnn_Param_t params__dec3_c1_norm_Reshape_GroupNorm[] = {
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="epsilon",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_FLOAT_32, {.floatValue = 0.000010000000f}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 8}}}}
  };
  const char*  inputs__dec3_c1_norm_Reshape_GroupNorm[] = {
    "_dec3_c1_point_Conv_output_0",
    "onnx__Mul_784",
    "onnx__Add_785"
  };
  uint32_t dimensions__dec3_c1_act_Relu_output_0[] = {1, 64, 64, 192};
  Qnn_Tensor_t outputs__dec3_c1_norm_Reshape_GroupNorm[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_dec3_c1_act_Relu_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0169817693531513f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__dec3_c1_act_Relu_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_dec3_c1_norm_Reshape_GroupNorm", // Node Name
                         "qti.aisw", // Package Name
                         "GroupNorm", // Qnn Node Type
                         params__dec3_c1_norm_Reshape_GroupNorm, // Node Params
                         2, // Num Node Params
                         inputs__dec3_c1_norm_Reshape_GroupNorm, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__dec3_c1_norm_Reshape_GroupNorm, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_dec3_c2_depth_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_dec3_c2_depth_weight[] = {3, 3, 1, 192};
  VALIDATE(model.addTensor("dec3_c2_depth_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "dec3_c2_depth_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0031370457727462f, .offset= -119}}},
                                 .rank= 4,
                                 .dimensions=dimensions_dec3_c2_depth_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(dec3_c2_depth_weight),
                                                .dataSize=BINLEN(dec3_c2_depth_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__dec3_c2_depth_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__dec3_c2_depth_Conv_bias[] = {192};
  VALIDATE(model.addTensor("_dec3_c2_depth_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_dec3_c2_depth_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__dec3_c2_depth_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_dec3_c2_depth_Conv_bias),
                                                .dataSize=BINLEN(_dec3_c2_depth_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__dec3_c2_depth_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _dec3_c2_depth_Conv */
  uint32_t dimensions___dec3_c2_depth_Conv_dilation[] = {2};
  uint32_t __dec3_c2_depth_Conv_dilation[] = {1, 1};
  uint32_t dimensions___dec3_c2_depth_Conv_pad_amount[] = {2, 2};
  uint32_t __dec3_c2_depth_Conv_pad_amount[] = {1, 1, 1, 1};
  uint32_t dimensions___dec3_c2_depth_Conv_stride[] = {2};
  uint32_t __dec3_c2_depth_Conv_stride[] = {1, 1};
  Qnn_Param_t params__dec3_c2_depth_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec3_c2_depth_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___dec3_c2_depth_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec3_c2_depth_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec3_c2_depth_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___dec3_c2_depth_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec3_c2_depth_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec3_c2_depth_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___dec3_c2_depth_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec3_c2_depth_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}}
  };
  const char*  inputs__dec3_c2_depth_Conv[] = {
    "_dec3_c1_act_Relu_output_0",
    "dec3_c2_depth_weight",
    "_dec3_c2_depth_Conv_bias"
  };
  uint32_t dimensions__dec3_c2_depth_Conv_output_0[] = {1, 64, 64, 192};
  Qnn_Tensor_t outputs__dec3_c2_depth_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_dec3_c2_depth_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0197742357850075f, .offset= -104}}},
            .rank= 4,
            .dimensions=dimensions__dec3_c2_depth_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_dec3_c2_depth_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "DepthWiseConv2d", // Qnn Node Type
                         params__dec3_c2_depth_Conv, // Node Params
                         3, // Num Node Params
                         inputs__dec3_c2_depth_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__dec3_c2_depth_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_dec3_c2_point_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_dec3_c2_point_weight[] = {1, 1, 192, 192};
  VALIDATE(model.addTensor("dec3_c2_point_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "dec3_c2_point_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0024163334164768f, .offset= -131}}},
                                 .rank= 4,
                                 .dimensions=dimensions_dec3_c2_point_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(dec3_c2_point_weight),
                                                .dataSize=BINLEN(dec3_c2_point_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__dec3_c2_point_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__dec3_c2_point_Conv_bias[] = {192};
  VALIDATE(model.addTensor("_dec3_c2_point_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_dec3_c2_point_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__dec3_c2_point_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_dec3_c2_point_Conv_bias),
                                                .dataSize=BINLEN(_dec3_c2_point_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__dec3_c2_point_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _dec3_c2_point_Conv */
  uint32_t dimensions___dec3_c2_point_Conv_dilation[] = {2};
  uint32_t __dec3_c2_point_Conv_dilation[] = {1, 1};
  uint32_t dimensions___dec3_c2_point_Conv_pad_amount[] = {2, 2};
  uint32_t __dec3_c2_point_Conv_pad_amount[] = {0, 0, 0, 0};
  uint32_t dimensions___dec3_c2_point_Conv_stride[] = {2};
  uint32_t __dec3_c2_point_Conv_stride[] = {1, 1};
  Qnn_Param_t params__dec3_c2_point_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec3_c2_point_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___dec3_c2_point_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec3_c2_point_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec3_c2_point_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___dec3_c2_point_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec3_c2_point_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec3_c2_point_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___dec3_c2_point_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec3_c2_point_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 1}}}}
  };
  const char*  inputs__dec3_c2_point_Conv[] = {
    "_dec3_c2_depth_Conv_output_0",
    "dec3_c2_point_weight",
    "_dec3_c2_point_Conv_bias"
  };
  uint32_t dimensions__dec3_c2_point_Conv_output_0[] = {1, 64, 64, 192};
  Qnn_Tensor_t outputs__dec3_c2_point_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_dec3_c2_point_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0070137991569936f, .offset= -141}}},
            .rank= 4,
            .dimensions=dimensions__dec3_c2_point_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_dec3_c2_point_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "Conv2d", // Qnn Node Type
                         params__dec3_c2_point_Conv, // Node Params
                         4, // Num Node Params
                         inputs__dec3_c2_point_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__dec3_c2_point_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Mul_791(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Mul_791[] = {192};
  VALIDATE(model.addTensor("onnx__Mul_791", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Mul_791",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0049334503710270f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Mul_791,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Mul_791),
                                                .dataSize=BINLEN(onnx__Mul_791)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Add_792(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Add_792[] = {192};
  VALIDATE(model.addTensor("onnx__Add_792", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Add_792",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0009540550527163f, .offset= -89}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Add_792,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Add_792),
                                                .dataSize=BINLEN(onnx__Add_792)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__dec3_c2_norm_Reshape_GroupNorm(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _dec3_c2_norm_Reshape_GroupNorm */
  Qnn_Param_t params__dec3_c2_norm_Reshape_GroupNorm[] = {
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="epsilon",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_FLOAT_32, {.floatValue = 0.000010000000f}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 8}}}}
  };
  const char*  inputs__dec3_c2_norm_Reshape_GroupNorm[] = {
    "_dec3_c2_point_Conv_output_0",
    "onnx__Mul_791",
    "onnx__Add_792"
  };
  uint32_t dimensions__dec3_c2_act_Relu_output_0[] = {1, 64, 64, 192};
  Qnn_Tensor_t outputs__dec3_c2_norm_Reshape_GroupNorm[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_dec3_c2_act_Relu_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0290475208312273f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__dec3_c2_act_Relu_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_dec3_c2_norm_Reshape_GroupNorm", // Node Name
                         "qti.aisw", // Package Name
                         "GroupNorm", // Qnn Node Type
                         params__dec3_c2_norm_Reshape_GroupNorm, // Node Params
                         2, // Num Node Params
                         inputs__dec3_c2_norm_Reshape_GroupNorm, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__dec3_c2_norm_Reshape_GroupNorm, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addNode__Resize_1(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _Resize_1 */
  Qnn_Param_t params__Resize_1[] = {
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="align_corners",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_BOOL_8, {.bool8Value = 0}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="antialias",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_BOOL_8, {.bool8Value = 0}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="half_pixel_centers",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_BOOL_8, {.bool8Value = 1}}}}
  };
  const char*  inputs__Resize_1[] = {
    "_dec3_c2_act_Relu_output_0"
  };
  uint32_t dimensions__Resize_1_output_0[] = {1, 128, 128, 192};
  Qnn_Tensor_t outputs__Resize_1[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_Resize_1_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0290475208312273f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__Resize_1_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_Resize_1", // Node Name
                         "qti.aisw", // Package Name
                         "ResizeBilinear", // Qnn Node Type
                         params__Resize_1, // Node Params
                         3, // Num Node Params
                         inputs__Resize_1, // Input Tensor Names
                         1, // Num Input Tensor Names
                         outputs__Resize_1, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addNode__Concat_5(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _Concat_5 */
  Qnn_Param_t params__Concat_5[] = {
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="axis",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 3}}}}
  };
  const char*  inputs__Concat_5[] = {
    "_Resize_1_output_0",
    "_enc2_c2_act_Relu_output_0"
  };
  uint32_t dimensions__Concat_5_output_0[] = {1, 128, 128, 288};
  Qnn_Tensor_t outputs__Concat_5[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_Concat_5_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0290475208312273f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__Concat_5_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_Concat_5", // Node Name
                         "qti.aisw", // Package Name
                         "Concat", // Qnn Node Type
                         params__Concat_5, // Node Params
                         1, // Num Node Params
                         inputs__Concat_5, // Input Tensor Names
                         2, // Num Input Tensor Names
                         outputs__Concat_5, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_dec2_c1_depth_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_dec2_c1_depth_weight[] = {3, 3, 1, 288};
  VALIDATE(model.addTensor("dec2_c1_depth_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "dec2_c1_depth_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0030811976175755f, .offset= -127}}},
                                 .rank= 4,
                                 .dimensions=dimensions_dec2_c1_depth_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(dec2_c1_depth_weight),
                                                .dataSize=BINLEN(dec2_c1_depth_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__dec2_c1_depth_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__dec2_c1_depth_Conv_bias[] = {288};
  VALIDATE(model.addTensor("_dec2_c1_depth_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_dec2_c1_depth_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__dec2_c1_depth_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_dec2_c1_depth_Conv_bias),
                                                .dataSize=BINLEN(_dec2_c1_depth_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__dec2_c1_depth_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _dec2_c1_depth_Conv */
  uint32_t dimensions___dec2_c1_depth_Conv_dilation[] = {2};
  uint32_t __dec2_c1_depth_Conv_dilation[] = {1, 1};
  uint32_t dimensions___dec2_c1_depth_Conv_pad_amount[] = {2, 2};
  uint32_t __dec2_c1_depth_Conv_pad_amount[] = {1, 1, 1, 1};
  uint32_t dimensions___dec2_c1_depth_Conv_stride[] = {2};
  uint32_t __dec2_c1_depth_Conv_stride[] = {1, 1};
  Qnn_Param_t params__dec2_c1_depth_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec2_c1_depth_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___dec2_c1_depth_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec2_c1_depth_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec2_c1_depth_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___dec2_c1_depth_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec2_c1_depth_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec2_c1_depth_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___dec2_c1_depth_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec2_c1_depth_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}}
  };
  const char*  inputs__dec2_c1_depth_Conv[] = {
    "_Concat_5_output_0",
    "dec2_c1_depth_weight",
    "_dec2_c1_depth_Conv_bias"
  };
  uint32_t dimensions__dec2_c1_depth_Conv_output_0[] = {1, 128, 128, 288};
  Qnn_Tensor_t outputs__dec2_c1_depth_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_dec2_c1_depth_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0388453602790833f, .offset= -181}}},
            .rank= 4,
            .dimensions=dimensions__dec2_c1_depth_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_dec2_c1_depth_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "DepthWiseConv2d", // Qnn Node Type
                         params__dec2_c1_depth_Conv, // Node Params
                         3, // Num Node Params
                         inputs__dec2_c1_depth_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__dec2_c1_depth_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_dec2_c1_point_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_dec2_c1_point_weight[] = {1, 1, 288, 96};
  VALIDATE(model.addTensor("dec2_c1_point_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "dec2_c1_point_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0024537332355976f, .offset= -137}}},
                                 .rank= 4,
                                 .dimensions=dimensions_dec2_c1_point_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(dec2_c1_point_weight),
                                                .dataSize=BINLEN(dec2_c1_point_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__dec2_c1_point_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__dec2_c1_point_Conv_bias[] = {96};
  VALIDATE(model.addTensor("_dec2_c1_point_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_dec2_c1_point_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__dec2_c1_point_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_dec2_c1_point_Conv_bias),
                                                .dataSize=BINLEN(_dec2_c1_point_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__dec2_c1_point_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _dec2_c1_point_Conv */
  uint32_t dimensions___dec2_c1_point_Conv_dilation[] = {2};
  uint32_t __dec2_c1_point_Conv_dilation[] = {1, 1};
  uint32_t dimensions___dec2_c1_point_Conv_pad_amount[] = {2, 2};
  uint32_t __dec2_c1_point_Conv_pad_amount[] = {0, 0, 0, 0};
  uint32_t dimensions___dec2_c1_point_Conv_stride[] = {2};
  uint32_t __dec2_c1_point_Conv_stride[] = {1, 1};
  Qnn_Param_t params__dec2_c1_point_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec2_c1_point_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___dec2_c1_point_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec2_c1_point_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec2_c1_point_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___dec2_c1_point_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec2_c1_point_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec2_c1_point_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___dec2_c1_point_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec2_c1_point_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 1}}}}
  };
  const char*  inputs__dec2_c1_point_Conv[] = {
    "_dec2_c1_depth_Conv_output_0",
    "dec2_c1_point_weight",
    "_dec2_c1_point_Conv_bias"
  };
  uint32_t dimensions__dec2_c1_point_Conv_output_0[] = {1, 128, 128, 96};
  Qnn_Tensor_t outputs__dec2_c1_point_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_dec2_c1_point_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0255581326782703f, .offset= -155}}},
            .rank= 4,
            .dimensions=dimensions__dec2_c1_point_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_dec2_c1_point_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "Conv2d", // Qnn Node Type
                         params__dec2_c1_point_Conv, // Node Params
                         4, // Num Node Params
                         inputs__dec2_c1_point_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__dec2_c1_point_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Mul_798(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Mul_798[] = {96};
  VALIDATE(model.addTensor("onnx__Mul_798", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Mul_798",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0046307323500514f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Mul_798,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Mul_798),
                                                .dataSize=BINLEN(onnx__Mul_798)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Add_799(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Add_799[] = {96};
  VALIDATE(model.addTensor("onnx__Add_799", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Add_799",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0007505544344895f, .offset= -72}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Add_799,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Add_799),
                                                .dataSize=BINLEN(onnx__Add_799)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__dec2_c1_norm_Reshape_GroupNorm(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _dec2_c1_norm_Reshape_GroupNorm */
  Qnn_Param_t params__dec2_c1_norm_Reshape_GroupNorm[] = {
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="epsilon",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_FLOAT_32, {.floatValue = 0.000010000000f}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 8}}}}
  };
  const char*  inputs__dec2_c1_norm_Reshape_GroupNorm[] = {
    "_dec2_c1_point_Conv_output_0",
    "onnx__Mul_798",
    "onnx__Add_799"
  };
  uint32_t dimensions__dec2_c1_act_Relu_output_0[] = {1, 128, 128, 96};
  Qnn_Tensor_t outputs__dec2_c1_norm_Reshape_GroupNorm[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_dec2_c1_act_Relu_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0291175339370966f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__dec2_c1_act_Relu_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_dec2_c1_norm_Reshape_GroupNorm", // Node Name
                         "qti.aisw", // Package Name
                         "GroupNorm", // Qnn Node Type
                         params__dec2_c1_norm_Reshape_GroupNorm, // Node Params
                         2, // Num Node Params
                         inputs__dec2_c1_norm_Reshape_GroupNorm, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__dec2_c1_norm_Reshape_GroupNorm, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_dec2_c2_depth_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_dec2_c2_depth_weight[] = {3, 3, 1, 96};
  VALIDATE(model.addTensor("dec2_c2_depth_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "dec2_c2_depth_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0030588628724217f, .offset= -125}}},
                                 .rank= 4,
                                 .dimensions=dimensions_dec2_c2_depth_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(dec2_c2_depth_weight),
                                                .dataSize=BINLEN(dec2_c2_depth_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__dec2_c2_depth_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__dec2_c2_depth_Conv_bias[] = {96};
  VALIDATE(model.addTensor("_dec2_c2_depth_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_dec2_c2_depth_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__dec2_c2_depth_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_dec2_c2_depth_Conv_bias),
                                                .dataSize=BINLEN(_dec2_c2_depth_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__dec2_c2_depth_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _dec2_c2_depth_Conv */
  uint32_t dimensions___dec2_c2_depth_Conv_dilation[] = {2};
  uint32_t __dec2_c2_depth_Conv_dilation[] = {1, 1};
  uint32_t dimensions___dec2_c2_depth_Conv_pad_amount[] = {2, 2};
  uint32_t __dec2_c2_depth_Conv_pad_amount[] = {1, 1, 1, 1};
  uint32_t dimensions___dec2_c2_depth_Conv_stride[] = {2};
  uint32_t __dec2_c2_depth_Conv_stride[] = {1, 1};
  Qnn_Param_t params__dec2_c2_depth_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec2_c2_depth_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___dec2_c2_depth_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec2_c2_depth_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec2_c2_depth_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___dec2_c2_depth_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec2_c2_depth_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec2_c2_depth_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___dec2_c2_depth_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec2_c2_depth_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}}
  };
  const char*  inputs__dec2_c2_depth_Conv[] = {
    "_dec2_c1_act_Relu_output_0",
    "dec2_c2_depth_weight",
    "_dec2_c2_depth_Conv_bias"
  };
  uint32_t dimensions__dec2_c2_depth_Conv_output_0[] = {1, 128, 128, 96};
  Qnn_Tensor_t outputs__dec2_c2_depth_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_dec2_c2_depth_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0484913624823093f, .offset= -186}}},
            .rank= 4,
            .dimensions=dimensions__dec2_c2_depth_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_dec2_c2_depth_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "DepthWiseConv2d", // Qnn Node Type
                         params__dec2_c2_depth_Conv, // Node Params
                         3, // Num Node Params
                         inputs__dec2_c2_depth_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__dec2_c2_depth_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_dec2_c2_point_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_dec2_c2_point_weight[] = {1, 1, 96, 96};
  VALIDATE(model.addTensor("dec2_c2_point_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "dec2_c2_point_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0029273508116603f, .offset= -151}}},
                                 .rank= 4,
                                 .dimensions=dimensions_dec2_c2_point_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(dec2_c2_point_weight),
                                                .dataSize=BINLEN(dec2_c2_point_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__dec2_c2_point_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__dec2_c2_point_Conv_bias[] = {96};
  VALIDATE(model.addTensor("_dec2_c2_point_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_dec2_c2_point_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__dec2_c2_point_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_dec2_c2_point_Conv_bias),
                                                .dataSize=BINLEN(_dec2_c2_point_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__dec2_c2_point_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _dec2_c2_point_Conv */
  uint32_t dimensions___dec2_c2_point_Conv_dilation[] = {2};
  uint32_t __dec2_c2_point_Conv_dilation[] = {1, 1};
  uint32_t dimensions___dec2_c2_point_Conv_pad_amount[] = {2, 2};
  uint32_t __dec2_c2_point_Conv_pad_amount[] = {0, 0, 0, 0};
  uint32_t dimensions___dec2_c2_point_Conv_stride[] = {2};
  uint32_t __dec2_c2_point_Conv_stride[] = {1, 1};
  Qnn_Param_t params__dec2_c2_point_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec2_c2_point_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___dec2_c2_point_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec2_c2_point_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec2_c2_point_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___dec2_c2_point_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec2_c2_point_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec2_c2_point_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___dec2_c2_point_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec2_c2_point_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 1}}}}
  };
  const char*  inputs__dec2_c2_point_Conv[] = {
    "_dec2_c2_depth_Conv_output_0",
    "dec2_c2_point_weight",
    "_dec2_c2_point_Conv_bias"
  };
  uint32_t dimensions__dec2_c2_point_Conv_output_0[] = {1, 128, 128, 96};
  Qnn_Tensor_t outputs__dec2_c2_point_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_dec2_c2_point_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0209043249487877f, .offset= -154}}},
            .rank= 4,
            .dimensions=dimensions__dec2_c2_point_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_dec2_c2_point_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "Conv2d", // Qnn Node Type
                         params__dec2_c2_point_Conv, // Node Params
                         4, // Num Node Params
                         inputs__dec2_c2_point_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__dec2_c2_point_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Mul_805(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Mul_805[] = {96};
  VALIDATE(model.addTensor("onnx__Mul_805", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Mul_805",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0047992174513638f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Mul_805,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Mul_805),
                                                .dataSize=BINLEN(onnx__Mul_805)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Add_806(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Add_806[] = {96};
  VALIDATE(model.addTensor("onnx__Add_806", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Add_806",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0008666035137139f, .offset= -73}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Add_806,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Add_806),
                                                .dataSize=BINLEN(onnx__Add_806)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__dec2_c2_norm_Reshape_GroupNorm(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _dec2_c2_norm_Reshape_GroupNorm */
  Qnn_Param_t params__dec2_c2_norm_Reshape_GroupNorm[] = {
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="epsilon",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_FLOAT_32, {.floatValue = 0.000010000000f}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 8}}}}
  };
  const char*  inputs__dec2_c2_norm_Reshape_GroupNorm[] = {
    "_dec2_c2_point_Conv_output_0",
    "onnx__Mul_805",
    "onnx__Add_806"
  };
  uint32_t dimensions__dec2_c2_act_Relu_output_0[] = {1, 128, 128, 96};
  Qnn_Tensor_t outputs__dec2_c2_norm_Reshape_GroupNorm[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_dec2_c2_act_Relu_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0243606120347977f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__dec2_c2_act_Relu_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_dec2_c2_norm_Reshape_GroupNorm", // Node Name
                         "qti.aisw", // Package Name
                         "GroupNorm", // Qnn Node Type
                         params__dec2_c2_norm_Reshape_GroupNorm, // Node Params
                         2, // Num Node Params
                         inputs__dec2_c2_norm_Reshape_GroupNorm, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__dec2_c2_norm_Reshape_GroupNorm, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addNode__Resize_2(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _Resize_2 */
  Qnn_Param_t params__Resize_2[] = {
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="align_corners",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_BOOL_8, {.bool8Value = 0}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="antialias",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_BOOL_8, {.bool8Value = 0}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="half_pixel_centers",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_BOOL_8, {.bool8Value = 1}}}}
  };
  const char*  inputs__Resize_2[] = {
    "_dec2_c2_act_Relu_output_0"
  };
  uint32_t dimensions__Resize_2_output_0[] = {1, 256, 256, 96};
  Qnn_Tensor_t outputs__Resize_2[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_Resize_2_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0243606120347977f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__Resize_2_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_Resize_2", // Node Name
                         "qti.aisw", // Package Name
                         "ResizeBilinear", // Qnn Node Type
                         params__Resize_2, // Node Params
                         3, // Num Node Params
                         inputs__Resize_2, // Input Tensor Names
                         1, // Num Input Tensor Names
                         outputs__Resize_2, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addNode__Concat_8(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _Concat_8 */
  Qnn_Param_t params__Concat_8[] = {
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="axis",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 3}}}}
  };
  const char*  inputs__Concat_8[] = {
    "_Resize_2_output_0",
    "_enc1_c2_act_Relu_output_0"
  };
  uint32_t dimensions__Concat_8_output_0[] = {1, 256, 256, 144};
  Qnn_Tensor_t outputs__Concat_8[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_Concat_8_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0351408384740353f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__Concat_8_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_Concat_8", // Node Name
                         "qti.aisw", // Package Name
                         "Concat", // Qnn Node Type
                         params__Concat_8, // Node Params
                         1, // Num Node Params
                         inputs__Concat_8, // Input Tensor Names
                         2, // Num Input Tensor Names
                         outputs__Concat_8, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_dec1_c1_depth_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_dec1_c1_depth_weight[] = {3, 3, 1, 144};
  VALIDATE(model.addTensor("dec1_c1_depth_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "dec1_c1_depth_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0035612499341369f, .offset= -132}}},
                                 .rank= 4,
                                 .dimensions=dimensions_dec1_c1_depth_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(dec1_c1_depth_weight),
                                                .dataSize=BINLEN(dec1_c1_depth_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__dec1_c1_depth_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__dec1_c1_depth_Conv_bias[] = {144};
  VALIDATE(model.addTensor("_dec1_c1_depth_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_dec1_c1_depth_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__dec1_c1_depth_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_dec1_c1_depth_Conv_bias),
                                                .dataSize=BINLEN(_dec1_c1_depth_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__dec1_c1_depth_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _dec1_c1_depth_Conv */
  uint32_t dimensions___dec1_c1_depth_Conv_dilation[] = {2};
  uint32_t __dec1_c1_depth_Conv_dilation[] = {1, 1};
  uint32_t dimensions___dec1_c1_depth_Conv_pad_amount[] = {2, 2};
  uint32_t __dec1_c1_depth_Conv_pad_amount[] = {1, 1, 1, 1};
  uint32_t dimensions___dec1_c1_depth_Conv_stride[] = {2};
  uint32_t __dec1_c1_depth_Conv_stride[] = {1, 1};
  Qnn_Param_t params__dec1_c1_depth_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec1_c1_depth_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___dec1_c1_depth_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec1_c1_depth_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec1_c1_depth_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___dec1_c1_depth_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec1_c1_depth_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec1_c1_depth_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___dec1_c1_depth_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec1_c1_depth_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}}
  };
  const char*  inputs__dec1_c1_depth_Conv[] = {
    "_Concat_8_output_0",
    "dec1_c1_depth_weight",
    "_dec1_c1_depth_Conv_bias"
  };
  uint32_t dimensions__dec1_c1_depth_Conv_output_0[] = {1, 256, 256, 144};
  Qnn_Tensor_t outputs__dec1_c1_depth_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_dec1_c1_depth_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0446259416639805f, .offset= -112}}},
            .rank= 4,
            .dimensions=dimensions__dec1_c1_depth_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_dec1_c1_depth_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "DepthWiseConv2d", // Qnn Node Type
                         params__dec1_c1_depth_Conv, // Node Params
                         3, // Num Node Params
                         inputs__dec1_c1_depth_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__dec1_c1_depth_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_dec1_c1_point_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_dec1_c1_point_weight[] = {1, 1, 144, 48};
  VALIDATE(model.addTensor("dec1_c1_point_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "dec1_c1_point_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0036739809438586f, .offset= -145}}},
                                 .rank= 4,
                                 .dimensions=dimensions_dec1_c1_point_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(dec1_c1_point_weight),
                                                .dataSize=BINLEN(dec1_c1_point_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__dec1_c1_point_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__dec1_c1_point_Conv_bias[] = {48};
  VALIDATE(model.addTensor("_dec1_c1_point_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_dec1_c1_point_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__dec1_c1_point_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_dec1_c1_point_Conv_bias),
                                                .dataSize=BINLEN(_dec1_c1_point_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__dec1_c1_point_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _dec1_c1_point_Conv */
  uint32_t dimensions___dec1_c1_point_Conv_dilation[] = {2};
  uint32_t __dec1_c1_point_Conv_dilation[] = {1, 1};
  uint32_t dimensions___dec1_c1_point_Conv_pad_amount[] = {2, 2};
  uint32_t __dec1_c1_point_Conv_pad_amount[] = {0, 0, 0, 0};
  uint32_t dimensions___dec1_c1_point_Conv_stride[] = {2};
  uint32_t __dec1_c1_point_Conv_stride[] = {1, 1};
  Qnn_Param_t params__dec1_c1_point_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec1_c1_point_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___dec1_c1_point_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec1_c1_point_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec1_c1_point_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___dec1_c1_point_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec1_c1_point_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec1_c1_point_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___dec1_c1_point_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec1_c1_point_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 1}}}}
  };
  const char*  inputs__dec1_c1_point_Conv[] = {
    "_dec1_c1_depth_Conv_output_0",
    "dec1_c1_point_weight",
    "_dec1_c1_point_Conv_bias"
  };
  uint32_t dimensions__dec1_c1_point_Conv_output_0[] = {1, 256, 256, 48};
  Qnn_Tensor_t outputs__dec1_c1_point_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_dec1_c1_point_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0241003967821598f, .offset= -144}}},
            .rank= 4,
            .dimensions=dimensions__dec1_c1_point_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_dec1_c1_point_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "Conv2d", // Qnn Node Type
                         params__dec1_c1_point_Conv, // Node Params
                         4, // Num Node Params
                         inputs__dec1_c1_point_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__dec1_c1_point_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Mul_812(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Mul_812[] = {48};
  VALIDATE(model.addTensor("onnx__Mul_812", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Mul_812",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0059180227108300f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Mul_812,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Mul_812),
                                                .dataSize=BINLEN(onnx__Mul_812)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Add_813(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Add_813[] = {48};
  VALIDATE(model.addTensor("onnx__Add_813", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Add_813",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0003895145200659f, .offset= -135}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Add_813,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Add_813),
                                                .dataSize=BINLEN(onnx__Add_813)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__dec1_c1_norm_Reshape_GroupNorm(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _dec1_c1_norm_Reshape_GroupNorm */
  Qnn_Param_t params__dec1_c1_norm_Reshape_GroupNorm[] = {
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="epsilon",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_FLOAT_32, {.floatValue = 0.000010000000f}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 8}}}}
  };
  const char*  inputs__dec1_c1_norm_Reshape_GroupNorm[] = {
    "_dec1_c1_point_Conv_output_0",
    "onnx__Mul_812",
    "onnx__Add_813"
  };
  uint32_t dimensions__dec1_c1_act_Relu_output_0[] = {1, 256, 256, 48};
  Qnn_Tensor_t outputs__dec1_c1_norm_Reshape_GroupNorm[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_dec1_c1_act_Relu_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0243290420621634f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__dec1_c1_act_Relu_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_dec1_c1_norm_Reshape_GroupNorm", // Node Name
                         "qti.aisw", // Package Name
                         "GroupNorm", // Qnn Node Type
                         params__dec1_c1_norm_Reshape_GroupNorm, // Node Params
                         2, // Num Node Params
                         inputs__dec1_c1_norm_Reshape_GroupNorm, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__dec1_c1_norm_Reshape_GroupNorm, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_dec1_c2_depth_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_dec1_c2_depth_weight[] = {3, 3, 1, 48};
  VALIDATE(model.addTensor("dec1_c2_depth_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "dec1_c2_depth_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0047190538607538f, .offset= -156}}},
                                 .rank= 4,
                                 .dimensions=dimensions_dec1_c2_depth_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(dec1_c2_depth_weight),
                                                .dataSize=BINLEN(dec1_c2_depth_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__dec1_c2_depth_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__dec1_c2_depth_Conv_bias[] = {48};
  VALIDATE(model.addTensor("_dec1_c2_depth_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_dec1_c2_depth_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__dec1_c2_depth_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_dec1_c2_depth_Conv_bias),
                                                .dataSize=BINLEN(_dec1_c2_depth_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__dec1_c2_depth_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _dec1_c2_depth_Conv */
  uint32_t dimensions___dec1_c2_depth_Conv_dilation[] = {2};
  uint32_t __dec1_c2_depth_Conv_dilation[] = {1, 1};
  uint32_t dimensions___dec1_c2_depth_Conv_pad_amount[] = {2, 2};
  uint32_t __dec1_c2_depth_Conv_pad_amount[] = {1, 1, 1, 1};
  uint32_t dimensions___dec1_c2_depth_Conv_stride[] = {2};
  uint32_t __dec1_c2_depth_Conv_stride[] = {1, 1};
  Qnn_Param_t params__dec1_c2_depth_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec1_c2_depth_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___dec1_c2_depth_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec1_c2_depth_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec1_c2_depth_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___dec1_c2_depth_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec1_c2_depth_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec1_c2_depth_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___dec1_c2_depth_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec1_c2_depth_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}}
  };
  const char*  inputs__dec1_c2_depth_Conv[] = {
    "_dec1_c1_act_Relu_output_0",
    "dec1_c2_depth_weight",
    "_dec1_c2_depth_Conv_bias"
  };
  uint32_t dimensions__dec1_c2_depth_Conv_output_0[] = {1, 256, 256, 48};
  Qnn_Tensor_t outputs__dec1_c2_depth_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_dec1_c2_depth_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0364157482981682f, .offset= -119}}},
            .rank= 4,
            .dimensions=dimensions__dec1_c2_depth_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_dec1_c2_depth_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "DepthWiseConv2d", // Qnn Node Type
                         params__dec1_c2_depth_Conv, // Node Params
                         3, // Num Node Params
                         inputs__dec1_c2_depth_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__dec1_c2_depth_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_dec1_c2_point_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_dec1_c2_point_weight[] = {1, 1, 48, 48};
  VALIDATE(model.addTensor("dec1_c2_point_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "dec1_c2_point_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0038125342689455f, .offset= -123}}},
                                 .rank= 4,
                                 .dimensions=dimensions_dec1_c2_point_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(dec1_c2_point_weight),
                                                .dataSize=BINLEN(dec1_c2_point_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor__dec1_c2_point_Conv_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions__dec1_c2_point_Conv_bias[] = {48};
  VALIDATE(model.addTensor("_dec1_c2_point_Conv_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "_dec1_c2_point_Conv_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0000003921568634f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions__dec1_c2_point_Conv_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(_dec1_c2_point_Conv_bias),
                                                .dataSize=BINLEN(_dec1_c2_point_Conv_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__dec1_c2_point_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _dec1_c2_point_Conv */
  uint32_t dimensions___dec1_c2_point_Conv_dilation[] = {2};
  uint32_t __dec1_c2_point_Conv_dilation[] = {1, 1};
  uint32_t dimensions___dec1_c2_point_Conv_pad_amount[] = {2, 2};
  uint32_t __dec1_c2_point_Conv_pad_amount[] = {0, 0, 0, 0};
  uint32_t dimensions___dec1_c2_point_Conv_stride[] = {2};
  uint32_t __dec1_c2_point_Conv_stride[] = {1, 1};
  Qnn_Param_t params__dec1_c2_point_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec1_c2_point_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___dec1_c2_point_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec1_c2_point_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec1_c2_point_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___dec1_c2_point_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec1_c2_point_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__dec1_c2_point_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___dec1_c2_point_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__dec1_c2_point_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 1}}}}
  };
  const char*  inputs__dec1_c2_point_Conv[] = {
    "_dec1_c2_depth_Conv_output_0",
    "dec1_c2_point_weight",
    "_dec1_c2_point_Conv_bias"
  };
  uint32_t dimensions__dec1_c2_point_Conv_output_0[] = {1, 256, 256, 48};
  Qnn_Tensor_t outputs__dec1_c2_point_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_dec1_c2_point_Conv_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0182423852384090f, .offset= -153}}},
            .rank= 4,
            .dimensions=dimensions__dec1_c2_point_Conv_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_dec1_c2_point_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "Conv2d", // Qnn Node Type
                         params__dec1_c2_point_Conv, // Node Params
                         4, // Num Node Params
                         inputs__dec1_c2_point_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__dec1_c2_point_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Mul_819(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Mul_819[] = {48};
  VALIDATE(model.addTensor("onnx__Mul_819", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Mul_819",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0041121058166027f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Mul_819,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Mul_819),
                                                .dataSize=BINLEN(onnx__Mul_819)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor_onnx__Add_820(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_onnx__Add_820[] = {48};
  VALIDATE(model.addTensor("onnx__Add_820", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "onnx__Add_820",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0004174488130957f, .offset= -131}}},
                                 .rank= 1,
                                 .dimensions=dimensions_onnx__Add_820,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(onnx__Add_820),
                                                .dataSize=BINLEN(onnx__Add_820)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__dec1_c2_norm_Reshape_GroupNorm(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _dec1_c2_norm_Reshape_GroupNorm */
  Qnn_Param_t params__dec1_c2_norm_Reshape_GroupNorm[] = {
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="epsilon",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_FLOAT_32, {.floatValue = 0.000010000000f}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 8}}}}
  };
  const char*  inputs__dec1_c2_norm_Reshape_GroupNorm[] = {
    "_dec1_c2_point_Conv_output_0",
    "onnx__Mul_819",
    "onnx__Add_820"
  };
  uint32_t dimensions__dec1_c2_act_Relu_output_0[] = {1, 256, 256, 48};
  Qnn_Tensor_t outputs__dec1_c2_norm_Reshape_GroupNorm[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "_dec1_c2_act_Relu_output_0",
            .type= QNN_TENSOR_TYPE_NATIVE,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0214400663971901f, .offset= 0}}},
            .rank= 4,
            .dimensions=dimensions__dec1_c2_act_Relu_output_0,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_dec1_c2_norm_Reshape_GroupNorm", // Node Name
                         "qti.aisw", // Package Name
                         "GroupNorm", // Qnn Node Type
                         params__dec1_c2_norm_Reshape_GroupNorm, // Node Params
                         2, // Num Node Params
                         inputs__dec1_c2_norm_Reshape_GroupNorm, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__dec1_c2_norm_Reshape_GroupNorm, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

static ModelError_t addTensor_head_weight(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_head_weight[] = {1, 1, 48, 1};
  VALIDATE(model.addTensor("head_weight", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "head_weight",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0013136368943378f, .offset= -124}}},
                                 .rank= 4,
                                 .dimensions=dimensions_head_weight,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(head_weight),
                                                .dataSize=BINLEN(head_weight)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addTensor_head_bias(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;
  uint32_t dimensions_head_bias[] = {1};
  VALIDATE(model.addTensor("head_bias", // Tensor Name
                           (Qnn_Tensor_t) {
                               .version= QNN_TENSOR_VERSION_2,
                               {.v2= {
                                 .id=0,
                                 .name= "head_bias",
                                 .type= QNN_TENSOR_TYPE_STATIC,
                                 .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
                                 .dataType= QNN_DATATYPE_UFIXED_POINT_8,
                                 .quantizeParams= { QNN_DEFINITION_DEFINED,
                                                    QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                                                    {.scaleOffsetEncoding= {.scale= 0.0002408102300251f, .offset= 0}}},
                                 .rank= 1,
                                 .dimensions=dimensions_head_bias,
                                 .memType= QNN_TENSORMEMTYPE_RAW,
                                 {.clientBuf= { .data=BINVARSTART(head_bias),
                                                .dataSize=BINLEN(head_bias)}},
                                 .isDynamicDimensions= nullptr,
                                 .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                                                  .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
                                 .isProduced= 0}}}
  ), err);
  return err;
}

static ModelError_t addNode__head_Conv(QnnModel& model){
  ModelError_t err = MODEL_NO_ERROR;

  /* ADDING NODE FOR _head_Conv */
  uint32_t dimensions___head_Conv_dilation[] = {2};
  uint32_t __head_Conv_dilation[] = {1, 1};
  uint32_t dimensions___head_Conv_pad_amount[] = {2, 2};
  uint32_t __head_Conv_pad_amount[] = {0, 0, 0, 0};
  uint32_t dimensions___head_Conv_stride[] = {2};
  uint32_t __head_Conv_stride[] = {1, 1};
  Qnn_Param_t params__head_Conv[] = {
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="dilation",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__head_Conv_dilation",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___head_Conv_dilation,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__head_Conv_dilation,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="pad_amount",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__head_Conv_pad_amount",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 2,
            .dimensions=dimensions___head_Conv_pad_amount,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__head_Conv_pad_amount,
                           .dataSize=16}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_TENSOR,
     .name="stride",
     {.tensorParam=(Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "__head_Conv_stride",
            .type= QNN_TENSOR_TYPE_STATIC,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UINT_32,
            .quantizeParams= { QNN_DEFINITION_UNDEFINED,
                               QNN_QUANTIZATION_ENCODING_UNDEFINED,
                               {.scaleOffsetEncoding= {.scale= 0.0000000000000000f, .offset= 0}}},
            .rank= 1,
            .dimensions=dimensions___head_Conv_stride,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=(uint8_t*)__head_Conv_stride,
                           .dataSize=8}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}}},
    {.paramType=QNN_PARAMTYPE_SCALAR,
     .name="group",
     {.scalarParam= (Qnn_Scalar_t) {QNN_DATATYPE_UINT_32, {.uint32Value = 1}}}}
  };
  const char*  inputs__head_Conv[] = {
    "_dec1_c2_act_Relu_output_0",
    "head_weight",
    "head_bias"
  };
  uint32_t dimensions_output[] = {1, 256, 256, 1};
  Qnn_Tensor_t outputs__head_Conv[] = {
    (Qnn_Tensor_t) {
          .version= QNN_TENSOR_VERSION_2,
          {.v2= {
            .id=0,
            .name= "output",
            .type= QNN_TENSOR_TYPE_APP_READ,
            .dataFormat= QNN_TENSOR_DATA_FORMAT_DENSE,
            .dataType= QNN_DATATYPE_UFIXED_POINT_8,
            .quantizeParams= { QNN_DEFINITION_DEFINED,
                               QNN_QUANTIZATION_ENCODING_SCALE_OFFSET,
                               {.scaleOffsetEncoding= {.scale= 0.0111216781660914f, .offset= -163}}},
            .rank= 4,
            .dimensions=dimensions_output,
            .memType= QNN_TENSORMEMTYPE_RAW,
            {.clientBuf= { .data=nullptr,
                           .dataSize=0}},
            .isDynamicDimensions= nullptr,
            .sparseParams= { QNN_SPARSE_LAYOUT_UNDEFINED,
                             .hybridCoo= {.numSpecifiedElements= 0, .numSparseDimensions= 0}},
            .isProduced= 0}}}
  };
  VALIDATE(model.addNode(QNN_OPCONFIG_VERSION_1, // Op_Config_t Version
                         "_head_Conv", // Node Name
                         "qti.aisw", // Package Name
                         "Conv2d", // Qnn Node Type
                         params__head_Conv, // Node Params
                         4, // Num Node Params
                         inputs__head_Conv, // Input Tensor Names
                         3, // Num Input Tensor Names
                         outputs__head_Conv, // Output Tensors 
                         1// Num Output Tensors 
  ), err);
  return err;
}

QNN_API
ModelError_t QnnModel_composeGraphs(Qnn_BackendHandle_t backendHandle,
                                    QNN_INTERFACE_VER_TYPE interface,
                                    Qnn_ContextHandle_t contextHandle,
                                    const GraphConfigInfo_t** graphsConfigInfo,
                                    const uint32_t numGraphsConfigInfo,
                                    GraphInfoPtr_t** graphsInfo,
                                    uint32_t* numGraphsInfo,
                                    bool debug,
                                    QnnLog_Callback_t logCallback,
                                    QnnLog_Level_t maxLogLevel) {

  ModelError_t err = MODEL_NO_ERROR;

  /* model/graph for radio_map_liteunet_pad_constant_int8_qnn*/
  QnnModel radio_map_liteunet_pad_constant_int8_qnn;
  const QnnGraph_Config_t** graphConfigs = nullptr;
  VALIDATE(getQnnGraphConfigFromInfo("radio_map_liteunet_pad_constant_int8_qnn", graphsConfigInfo, numGraphsConfigInfo, graphConfigs), err);
  VALIDATE(radio_map_liteunet_pad_constant_int8_qnn.initialize(backendHandle, interface, contextHandle, "radio_map_liteunet_pad_constant_int8_qnn", debug, DO_GRAPH_NODE_VALIDATIONS, graphConfigs), err);
  VALIDATE(addTensor_input(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_enc1_c1_depth_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__enc1_c1_depth_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__enc1_c1_depth_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_enc1_c1_point_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__enc1_c1_point_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__enc1_c1_point_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Mul_728(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Add_729(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__enc1_c1_norm_Reshape_GroupNorm(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_enc1_c2_depth_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__enc1_c2_depth_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__enc1_c2_depth_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_enc1_c2_point_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__enc1_c2_point_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__enc1_c2_point_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Mul_735(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Add_736(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__enc1_c2_norm_Reshape_GroupNorm(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__pool_AveragePool(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_enc2_c1_depth_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__enc2_c1_depth_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__enc2_c1_depth_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_enc2_c1_point_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__enc2_c1_point_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__enc2_c1_point_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Mul_742(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Add_743(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__enc2_c1_norm_Reshape_GroupNorm(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_enc2_c2_depth_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__enc2_c2_depth_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__enc2_c2_depth_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_enc2_c2_point_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__enc2_c2_point_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__enc2_c2_point_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Mul_749(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Add_750(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__enc2_c2_norm_Reshape_GroupNorm(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__pool_1_AveragePool(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_enc3_c1_depth_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__enc3_c1_depth_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__enc3_c1_depth_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_enc3_c1_point_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__enc3_c1_point_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__enc3_c1_point_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Mul_756(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Add_757(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__enc3_c1_norm_Reshape_GroupNorm(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_enc3_c2_depth_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__enc3_c2_depth_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__enc3_c2_depth_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_enc3_c2_point_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__enc3_c2_point_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__enc3_c2_point_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Mul_763(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Add_764(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__enc3_c2_norm_Reshape_GroupNorm(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__pool_2_AveragePool(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_bottleneck_c1_depth_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__bottleneck_c1_depth_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__bottleneck_c1_depth_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_bottleneck_c1_point_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__bottleneck_c1_point_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__bottleneck_c1_point_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Mul_770(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Add_771(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__bottleneck_c1_norm_Reshape_GroupNorm(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_bottleneck_c2_depth_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__bottleneck_c2_depth_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__bottleneck_c2_depth_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_bottleneck_c2_point_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__bottleneck_c2_point_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__bottleneck_c2_point_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Mul_777(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Add_778(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__bottleneck_c2_norm_Reshape_GroupNorm(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Conv_709(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Conv_710(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__aspp_branches_0_branches_0_0_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Conv_712(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Conv_713(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__aspp_branches_1_branches_1_0_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Conv_715(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Conv_716(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__aspp_branches_2_branches_2_0_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Conv_718(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Conv_719(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__aspp_branches_3_branches_3_0_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__aspp_Concat(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Conv_721(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Conv_722(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__aspp_proj_proj_0_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__Resize(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__Concat_2(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_dec3_c1_depth_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__dec3_c1_depth_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__dec3_c1_depth_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_dec3_c1_point_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__dec3_c1_point_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__dec3_c1_point_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Mul_784(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Add_785(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__dec3_c1_norm_Reshape_GroupNorm(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_dec3_c2_depth_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__dec3_c2_depth_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__dec3_c2_depth_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_dec3_c2_point_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__dec3_c2_point_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__dec3_c2_point_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Mul_791(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Add_792(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__dec3_c2_norm_Reshape_GroupNorm(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__Resize_1(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__Concat_5(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_dec2_c1_depth_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__dec2_c1_depth_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__dec2_c1_depth_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_dec2_c1_point_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__dec2_c1_point_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__dec2_c1_point_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Mul_798(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Add_799(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__dec2_c1_norm_Reshape_GroupNorm(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_dec2_c2_depth_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__dec2_c2_depth_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__dec2_c2_depth_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_dec2_c2_point_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__dec2_c2_point_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__dec2_c2_point_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Mul_805(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Add_806(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__dec2_c2_norm_Reshape_GroupNorm(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__Resize_2(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__Concat_8(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_dec1_c1_depth_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__dec1_c1_depth_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__dec1_c1_depth_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_dec1_c1_point_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__dec1_c1_point_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__dec1_c1_point_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Mul_812(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Add_813(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__dec1_c1_norm_Reshape_GroupNorm(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_dec1_c2_depth_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__dec1_c2_depth_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__dec1_c2_depth_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_dec1_c2_point_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor__dec1_c2_point_Conv_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__dec1_c2_point_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Mul_819(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_onnx__Add_820(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__dec1_c2_norm_Reshape_GroupNorm(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_head_weight(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addTensor_head_bias(radio_map_liteunet_pad_constant_int8_qnn), err);
  VALIDATE(addNode__head_Conv(radio_map_liteunet_pad_constant_int8_qnn), err);

  // Add all models to array to get graphsInfo
  QnnModel* models [] = {&radio_map_liteunet_pad_constant_int8_qnn};
  uint32_t numModels = 1;

  // Populate the constructed graphs in provided output variables
  VALIDATE(getGraphInfoFromModels(*models, numModels, graphsInfo), err);
  *numGraphsInfo = numModels;

  return err;

} // PREPARE_GRAPHS

QNN_API
ModelError_t QnnModel_freeGraphsInfo(GraphInfoPtr_t** graphsInfo, uint32_t numGraphsInfo){
  return qnn_wrapper_api::freeGraphsInfo(graphsInfo, numGraphsInfo);
} // FREEGRAPHINFO

}