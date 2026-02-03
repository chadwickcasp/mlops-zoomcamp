variable "stream_name" {
  type        = string
  description = "The name of the Kinesis data stream"
}

variable "shard_count" {
  type        = number
  description = "The number of shards in the Kinesis data stream"
}

variable "retention_period" {
  type        = number
  description = "The retention period of the Kinesis data stream"
}

variable "shard_level_metrics" {
  type        = list(string)
  description = "The shard level metrics of the Kinesis data stream"
  default = [
    "IncomingBytes",
    "OutgoingBytes",
    "IncomingRecords",
    "OutgoingRecords",
    "IteratorAgeMilliseconds",
    "WriteProvisionedThroughputExceeded",
    "ReadProvisionedThroughputExceeded",
  ]
}

variable "tags" {
  description = "The tags of the Kinesis data stream"
  default     = "mlops-zoomcamp"
}
