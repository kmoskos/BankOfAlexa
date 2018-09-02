AWS.config.region = 'ap-southeast-2'; // Region
AWS.config.credentials = new AWS.CognitoIdentityCredentials({
    IdentityPoolId: 'ap-southeast-2:e950774e-1ee7-49cc-b3ac-fd6d09cbfe14',
});

var dynamodb = new AWS.DynamoDB({region: "us-east-1"});
var params = { TableName: 'BankOfAlexa' };

/* Create the context for applying the chart to the HTML canvas */
var ctx = $("#graph").get(0).getContext("2d");

/* Set the options for our chart */
var options = { segmentShowStroke : false,
								animateScale: true,
								percentageInnerCutout : 50,
                showToolTips: true,
                tooltipEvents: ["mousemove", "touchstart", "touchmove"],
                tooltipFontColor: "#fff",
								animationEasing : 'easeOutCirc'
              }

/* Set the inital data */
var init = [
  {
      value: 1,
      color:"#e74c3c",
      highlight: "#c0392b",
      label: "Debit"
  },
  {
      value: 1,
      color: "#2ecc71",
      highlight: "#27ae60",
      label: "Savings"
  },
  {
      value: 1,
      color: "#3498db",
      highlight: "#2980b9",
      label: "Credit"
  },
  {
      value: 1,
      color: "#8A2BE2",
      highlight: "#800080",
      label: "Mortgage"
  }
];

graph = new Chart(ctx).Doughnut(init, options);

$(function() {
  getData();
  $.ajaxSetup({ cache: false });
  setInterval(getData, 3000);
});

/* Makes a scan of the DynamoDB table to set a data object for the chart */
function getData() {
  dynamodb.scan(params, function(err, data) {
    if (err) {
      console.log(err);
      return null;
    } else {
      var redCount = 0;
      var greenCount = 0;
      var blueCount = 0;
      var purpleCount = 0;


      for (var i in data['Items']) {
        
        
        if (data['Items'][i]['account_type']['S'] == "debit") { 
          redCount = parseFloat(data['Items'][i]['balance']['S']);
        }
        if (data['Items'][i]['account_type']['S'] == "savings") {  
          greenCount = parseFloat(data['Items'][i]['balance']['S']);
        }
        if (data['Items'][i]['account_type']['S'] == "credit") {
          blueCount = parseFloat(data['Items'][i]['balance']['S']);
        }
        if (data['Items'][i]['account_type']['S'] == "mortgage") {
          purpleCount = parseFloat(data['Items'][i]['balance']['S']);
        }
      }

      var data = [
        {
            value: redCount,
            color:"#e74c3c",
            highlight: "#c0392b",
            label: "Debit"
        },
        {
            value: greenCount,
            color: "#2ecc71",
            highlight: "#27ae60",
            label: "Savings"
        },
        {
            value: blueCount,
            color: "#3498db",
            highlight: "#2980b9",
            label: "Credit"
        },
        {
            value: purpleCount,
            color: "#8A2BE2",
            highlight: "#800080",
            label: "Mortgage"
        }
      ];
      
      // Only update if we have new values (preserves tooltips)
      if (  graph.segments[0].value != data[0].value ||
            graph.segments[1].value != data[1].value ||
            graph.segments[2].value != data[2].value ||
            graph.segments[3].value != data[3].value
         )
      {
        graph.segments[0].value = data[0].value;
        graph.segments[1].value = data[1].value;
        graph.segments[2].value = data[2].value;
        graph.segments[3].value = data[3].value;
        graph.update();
      }

    }
  });
}
