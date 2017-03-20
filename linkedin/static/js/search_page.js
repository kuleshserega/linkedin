$(document).ready(function(){
    $('#searchbtn').on('click', function(e){
        e.preventDefault();
        var search_term = $('#id_search').val();
        $.ajax({
            url: '/run-search/?search=' + search_term,
            method: 'GET',
            success: function(data){
                console.log(data);
                window.location.reload();
            }
        });
    });

    var queryDict = {}
    location.search.substr(1).split("&").forEach(
        function(item){
            queryDict[item.split("=")[0]] = item.split("=")[1]
        }
    );
    setInterval(function(){
        if (queryDict["page"] != undefined){
            var page = queryDict['page'];
        } else {
            var page = 1;
        }

        var tbody_html = '<thead>' +
                          '<tr>' +
                            '<th>ID</th>' +
                            '<th>Search company</th>' +
                            '<th>Company ID</th>' +
                            '<th>Date</th>' +
                            '<th>Status</th>' +
                            '<th>Link to search details</th>' +
                            '<th>Save to CSV</th>' +
                          '</tr>' +
                        '</thead>';
        $.ajax({
            url: '/get_companies_list/?page=' + page,
            method: 'GET',
            success: function(data){
                for (var i=0;i<data['content'].length;i++){
                    tbody_html += '<tr>' +
                        '<td>' + data['content'][i]['id'] + '</td>' +
                        '<td>' + data['content'][i]['search_company'] + '</td>' +
                        '<td>' + data['content'][i]['companyId'] + '</td>' +
                        '<td>' + data['content'][i]['date_created'] + '</td>' +
                        '<td><span title="' + data['content'][i]['status_text'] + '" class="center glyphicon ' + data['content'][i]['status_icon'] + '"></span></td>' +
                        '<td><a title="Search details" class="center" href="' + data['content'][i]['search_details_url'] + '"><img width=25 src="/static/img/details.png" /></a></td>' +
                        '<td><a title="Save to CSV" class="center" href="' + data['content'][i]['employees_to_csv'] + '"><img width=25 src="/static/img/save.png" /></a></td>' +
                    '</tr>';
                }
                $('#allProjectsTable').html(tbody_html);
            }
        });        
    }, 5000);
});
