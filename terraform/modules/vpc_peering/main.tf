resource "aws_vpc_peering_connection" "this" {
  auto_accept = true
  peer_vpc_id = var.destination_vpc_id
  vpc_id      = var.source_vpc_id

  tags = merge(var.tags, {
    Name = var.name
  })
}

resource "aws_vpc_peering_connection_options" "this" {
  vpc_peering_connection_id = aws_vpc_peering_connection.this.id

  accepter {
    allow_remote_vpc_dns_resolution = var.enable_dns_resolution
  }

  requester {
    allow_remote_vpc_dns_resolution = var.enable_dns_resolution
  }
}

resource "aws_route" "source_to_destination" {
  count = var.enable_source_route ? length(var.source_route_table_ids) : 0

  destination_cidr_block    = var.destination_vpc_cidr
  route_table_id            = var.source_route_table_ids[count.index]
  vpc_peering_connection_id = aws_vpc_peering_connection.this.id
}

resource "aws_route" "destination_to_source" {
  count = var.enable_destination_route ? length(var.destination_route_table_ids) : 0

  destination_cidr_block    = var.source_vpc_cidr
  route_table_id            = var.destination_route_table_ids[count.index]
  vpc_peering_connection_id = aws_vpc_peering_connection.this.id
}
