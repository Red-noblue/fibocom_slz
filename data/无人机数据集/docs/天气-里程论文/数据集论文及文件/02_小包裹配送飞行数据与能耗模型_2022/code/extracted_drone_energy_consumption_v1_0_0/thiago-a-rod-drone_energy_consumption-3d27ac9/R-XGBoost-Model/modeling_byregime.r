# 中文说明：本文件用于按起飞/巡航/降落三个阶段训练 XGBoost 能耗模型，并兼容当前非 git 目录的本地复现环境。
library(plyr)
library(dplyr)
library(ggplot2)
library(reshape2)
library(xgboost)
library(pracma)

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
if (length(file_arg) > 0) {
  script_path <- normalizePath(sub("^--file=", "", file_arg[1]))
  modelR_dir <- dirname(script_path)
} else {
  modelR_dir <- normalizePath("R-XGBoost-Model")
}
source(file.path(modelR_dir, "helpers.r")) # functions for training model

skip_tuning <- tolower(Sys.getenv("SKIP_TUNING", unset = "0")) %in% c("1", "true", "yes")

vars_to_model <- c("flight", "time", "regime", "y",
  "wind_speed","wind_angle",
  "position_x","position_y","position_z",
  "orientation_x","orientation_y","orientation_z","orientation_w",
  "velocity_x","velocity_y","velocity_z",
  "angular_x","angular_y","angular_z",       
  "linear_acceleration_x","linear_acceleration_y","linear_acceleration_z",
  "payload"
)

df_all <- read.csv(file.path(modelR_dir, "../data/flights_processed.csv"))[,-1]
df_all$y <- df_all$battery_current*df_all$battery_voltage
df_all <- df_all %>% select(one_of(vars_to_model))

df_all_takeOff <- df_all %>% filter(regime == "takeoff") %>% select(-regime)
df_all_cruise <- df_all %>% filter(regime == "cruise") %>% select(-regime)
df_all_landing <- df_all %>% filter(regime == "landing") %>% select(-regime)

flights <- unique(df_all_takeOff$flight)
flights_train <- read.csv(file.path(modelR_dir, "../data/sample.csv"))[,1]

### takeOff
###########
idx_train <- which(df_all_takeOff$flight %in% flights_train)
df_train <- df_all_takeOff[idx_train,]
df_test <- df_all_takeOff[-idx_train,]

set.seed(1234)
if (!skip_tuning) {
  hyperpar_tuning_energy_model(df_train, regime_name = "takeOff")
} else {
  cat("SKIP_TUNING=1，跳过 takeOff 超参数搜索，直接使用论文选定参数训练最终模型。\n")
}

params <- list(nthread = 3,
               eta = 0.05, 
               gamma = 0, 
               max_depth = 3)
nrounds <- 250

set.seed(1234)
train_test_energy_model(df_train, df_test, params, nrounds, regime_name = "takeOff")


###########

### cruise
###########
idx_train <- which(df_all_cruise$flight %in% flights_train)
df_train <- df_all_cruise[idx_train,]
df_test <- df_all_cruise[-idx_train,]

set.seed(1234)
if (!skip_tuning) {
  hyperpar_tuning_energy_model(df_train, regime_name = "cruise")
} else {
  cat("SKIP_TUNING=1，跳过 cruise 超参数搜索，直接使用论文选定参数训练最终模型。\n")
}

params <- list(nthread = 3,
               eta = 0.1, 
               gamma = 5, 
               max_depth = 3)
nrounds <- 200
set.seed(1234)
train_test_energy_model(df_train, df_test, params, nrounds, regime_name = "cruise")

###########

### landing
###########
idx_train <- which(df_all_landing$flight %in% flights_train)
df_train <- df_all_landing[idx_train,]
df_test <- df_all_landing[-idx_train,]

set.seed(1234)
if (!skip_tuning) {
  hyperpar_tuning_energy_model(df_train, regime_name = "landing")
} else {
  cat("SKIP_TUNING=1，跳过 landing 超参数搜索，直接使用论文选定参数训练最终模型。\n")
}

params <- list(nthread = 3,
               eta = 0.1, 
               gamma = 5, 
               max_depth = 3)
nrounds <- 250
set.seed(1234)
train_test_energy_model(df_train, df_test, params, nrounds, regime_name = "landing")

###########
