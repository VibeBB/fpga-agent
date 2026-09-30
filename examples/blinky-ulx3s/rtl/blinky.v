// SPDX-License-Identifier: BSD-3-Clause
// Free-running counter shown on the eight ULX3S LEDs.
module blinky #(
    parameter integer WIDTH = 26
) (
    input  wire       clk_25mhz,
    output wire [7:0] led
);
  reg [WIDTH-1:0] count = {WIDTH{1'b0}};

  always @(posedge clk_25mhz) count <= count + 1'b1;

  assign led = count[WIDTH-1-:8];

`ifdef FORMAL
  reg past_valid = 1'b0;
  always @(posedge clk_25mhz) begin
    past_valid <= 1'b1;
    if (past_valid) assert (count == $past(count) + 1'b1);
  end
`endif
endmodule
