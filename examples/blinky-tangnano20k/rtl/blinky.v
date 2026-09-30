// SPDX-License-Identifier: BSD-3-Clause
// Binary counter on the six active-low LEDs of a Tang Nano 20K.
module blinky #(
    parameter integer WIDTH = 27
) (
    input  wire       clk,
    output wire [5:0] led_n
);
  reg [WIDTH-1:0] count = {WIDTH{1'b0}};

  always @(posedge clk) count <= count + 1'b1;

  assign led_n = ~count[WIDTH-1-:6];

`ifdef FORMAL
  reg past_valid = 1'b0;
  always @(posedge clk) begin
    past_valid <= 1'b1;
    if (past_valid) assert (count == $past(count) + 1'b1);
  end
`endif
endmodule
